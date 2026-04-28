from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from sqlalchemy.orm import Session

from backend.app.auth.deps import require_super_admin
from backend.app.db.deps import get_db
from backend.app.models.admin_user import AdminUser
from backend.app.schemas.content_schema import (
    BackgroundResponse,
    BannerCreate,
    BannerDeleteResponse,
    BannerResponse,
    BannerUpdate,
)
from backend.app.services.content_service import (
    create_banner,
    deactivate_banner,
    delete_banner,
    get_active_banners,
    get_all_banners,
    get_background,
    replace_background,
    save_content_image,
    update_banner,
)

router = APIRouter(prefix="/content", tags=["Content"])


# Background

@router.get("/background", response_model=BackgroundResponse)
def read_background(db: Session = Depends(get_db)):
    return get_background(db)


@router.put("/background", response_model=BackgroundResponse)
async def write_background(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return await replace_background(db, file)


# Banners

@router.get("/banners", response_model=list[BannerResponse])
def read_banners(db: Session = Depends(get_db)):
    return get_active_banners(db)


@router.get("/banners/all", response_model=list[BannerResponse])
def read_all_banners(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return get_all_banners(db)


@router.post("/banners", response_model=BannerResponse, status_code=status.HTTP_201_CREATED)
async def create_new_banner(
    file: UploadFile = File(...),
    title: str = Form(...),
    destination_code: str = Form(...),
    priority: int = Form(..., ge=1, le=8),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    image_url = await save_content_image(file)
    payload = BannerCreate(
        title=title,
        image_url=image_url,
        destination_code=destination_code,
        priority=priority,
    )
    return create_banner(db, payload)


@router.put("/banners/{banner_id}", response_model=BannerResponse)
async def update_existing_banner(
    banner_id: UUID,
    file: Optional[UploadFile] = File(None),
    title: Optional[str] = Form(None),
    destination_code: Optional[str] = Form(None),
    priority: Optional[int] = Form(None, ge=1, le=8),
    is_active: Optional[bool] = Form(None),
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    # Build update dict only from explicitly provided fields so that
    # exclude_unset=True in the service correctly skips omitted fields.
    update_fields: dict[str, Any] = {}
    if title is not None:
        update_fields["title"] = title
    if destination_code is not None:
        update_fields["destination_code"] = destination_code
    if priority is not None:
        update_fields["priority"] = priority
    if is_active is not None:
        update_fields["is_active"] = is_active
    if file and file.filename:
        update_fields["image_url"] = await save_content_image(file)

    return update_banner(db, banner_id, BannerUpdate(**update_fields))


@router.delete("/banners/{banner_id}", response_model=BannerResponse)
def deactivate_existing_banner(
    banner_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return deactivate_banner(db, banner_id)


@router.delete("/banners/{banner_id}/permanent", response_model=BannerDeleteResponse)
async def delete_existing_banner(
    banner_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    await delete_banner(db, banner_id)
    return {
        "message": "Banner permanently deleted successfully",
        "banner_id": banner_id,
    }
