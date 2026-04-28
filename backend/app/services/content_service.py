import json
import os
from uuid import UUID, uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.core.redis import redis_client
from backend.app.models.website_background import WebsiteBackground
from backend.app.models.website_banner import WebsiteBanner
from backend.app.schemas.content_schema import BackgroundUpdate, BannerCreate, BannerUpdate
from backend.app.services.storage_service import get_storage

_ALLOWED_CONTENT_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
_CONTENT_IMAGE_MAX_BYTES = 5 * 1024 * 1024  # 5MB
_CONTENT_IMAGE_SIGNATURES: dict[str, list[bytes]] = {
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    # WebP container starts with "RIFF" at bytes 0-3, "WEBP" at bytes 8-11
    "image/webp": [b"RIFF"],
}


async def save_content_image(file: UploadFile) -> str:
    if file.content_type not in _ALLOWED_CONTENT_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Allowed: image/jpeg, image/png, image/webp",
        )

    await file.seek(0)
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    await file.seek(0)

    if file_size > _CONTENT_IMAGE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum size is 5MB",
        )

    header = await file.read(16)
    await file.seek(0)

    expected_signatures = _CONTENT_IMAGE_SIGNATURES.get(file.content_type or "")
    if not expected_signatures or not any(
        header.startswith(sig) for sig in expected_signatures
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content does not match the declared file type",
        )

    extension = ""
    if file.filename and "." in file.filename:
        extension = f".{file.filename.rsplit('.', 1)[-1].lower()}"

    path = f"public/content/{uuid4().hex}{extension}"

    storage = get_storage()
    try:
        image_url = await storage.save(file, path)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage failure",
        ) from exc

    return image_url


_MAX_ACTIVE_BANNERS = 8
_BANNERS_CACHE_KEY = "content:banners:active"
_BANNERS_CACHE_TTL = 300  # 5 minutes


# Background

def get_background(db: Session) -> WebsiteBackground:
    bg = db.query(WebsiteBackground).filter(WebsiteBackground.id == 1).first()
    if not bg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Background image has not been set yet",
        )
    return bg


def upsert_background(db: Session, payload: BackgroundUpdate) -> WebsiteBackground:
    bg = db.query(WebsiteBackground).filter(WebsiteBackground.id == 1).first()
    if bg:
        bg.image_url = payload.image_url
    else:
        bg = WebsiteBackground(id=1, image_url=payload.image_url)
        db.add(bg)
    db.commit()
    db.refresh(bg)
    return bg


def _url_to_storage_path(url: str) -> str | None:
    idx = url.find("public/content/")
    if idx == -1:
        return None
    return url[idx:]


async def replace_background(db: Session, file: UploadFile) -> WebsiteBackground:
    old_bg = db.query(WebsiteBackground).filter(WebsiteBackground.id == 1).first()
    old_url = old_bg.image_url if old_bg else None

    image_url = await save_content_image(file)
    result = upsert_background(db, BackgroundUpdate(image_url=image_url))

    if old_url:
        path = _url_to_storage_path(old_url)
        if path:
            try:
                await get_storage().delete(path)
            except Exception:
                pass

    return result

# Banners

def _invalidate_banners_cache() -> None:
    try:
        redis_client.delete(_BANNERS_CACHE_KEY)
    except Exception:
        pass  # Cache miss on next request is acceptable


def get_all_banners(db: Session) -> list[dict]:
    rows = (
        db.query(WebsiteBanner)
        .order_by(WebsiteBanner.is_active.desc(), WebsiteBanner.priority.asc())
        .all()
    )
    return [
        {
            "id": str(row.id),
            "title": row.title,
            "image_url": row.image_url,
            "destination_code": row.destination_code,
            "priority": row.priority,
            "is_active": row.is_active,
        }
        for row in rows
    ]


def get_active_banners(db: Session) -> list[dict]:
    try:
        cached = redis_client.get(_BANNERS_CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception:
        pass  # Fall through to DB on Redis error

    rows = (
        db.query(WebsiteBanner)
        .filter(WebsiteBanner.is_active.is_(True))
        .order_by(WebsiteBanner.priority.asc())
        .limit(_MAX_ACTIVE_BANNERS)
        .all()
    )

    result = [
        {
            "id": str(row.id),
            "title": row.title,
            "image_url": row.image_url,
            "destination_code": row.destination_code,
            "priority": row.priority,
            "is_active": row.is_active,
        }
        for row in rows
    ]

    try:
        redis_client.setex(_BANNERS_CACHE_KEY, _BANNERS_CACHE_TTL, json.dumps(result))
    except Exception:
        pass

    return result


def _assert_priority_free(
    db: Session, priority: int, exclude_id: UUID | None = None
) -> None:
    query = db.query(WebsiteBanner).filter(
        WebsiteBanner.priority == priority,
        WebsiteBanner.is_active.is_(True),
    )
    if exclude_id is not None:
        query = query.filter(WebsiteBanner.id != exclude_id)
    if query.first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"An active banner with priority {priority} already exists",
        )


def _assert_under_limit(db: Session) -> None:
    count = (
        db.query(WebsiteBanner)
        .filter(WebsiteBanner.is_active.is_(True))
        .count()
    )
    if count >= _MAX_ACTIVE_BANNERS:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Maximum of {_MAX_ACTIVE_BANNERS} active banners already reached",
        )


def create_banner(db: Session, payload: BannerCreate) -> WebsiteBanner:
    _assert_under_limit(db)
    _assert_priority_free(db, payload.priority)

    banner = WebsiteBanner(**payload.model_dump())
    db.add(banner)
    db.commit()
    db.refresh(banner)
    _invalidate_banners_cache()
    return banner


def update_banner(db: Session, banner_id: UUID, payload: BannerUpdate) -> WebsiteBanner:
    banner = db.query(WebsiteBanner).filter(WebsiteBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Banner not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    # Activating an inactive banner counts toward the limit
    if update_data.get("is_active") is True and not banner.is_active:
        _assert_under_limit(db)

    new_priority = update_data.get("priority")
    if new_priority is not None:
        _assert_priority_free(db, new_priority, exclude_id=banner_id)

    for field, value in update_data.items():
        setattr(banner, field, value)

    db.commit()
    db.refresh(banner)
    _invalidate_banners_cache()
    return banner


def deactivate_banner(db: Session, banner_id: UUID) -> WebsiteBanner:
    banner = db.query(WebsiteBanner).filter(WebsiteBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Banner not found",
        )

    banner.is_active = False
    db.commit()
    db.refresh(banner)
    _invalidate_banners_cache()
    return banner


async def delete_banner(db: Session, banner_id: UUID) -> None:
    banner = db.query(WebsiteBanner).filter(WebsiteBanner.id == banner_id).first()
    if not banner:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Banner not found",
        )

    old_url = banner.image_url
    db.delete(banner)
    db.commit()
    _invalidate_banners_cache()

    path = _url_to_storage_path(old_url)
    if path:
        try:
            await get_storage().delete(path)
        except Exception:
            pass
