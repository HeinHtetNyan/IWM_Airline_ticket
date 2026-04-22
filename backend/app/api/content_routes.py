from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.deps import require_super_admin
from backend.app.db.deps import get_db
from backend.app.models.admin_user import AdminUser
from backend.app.schemas.content_schema import (
    BackgroundResponse,
    BackgroundUpdate,
    BannerCreate,
    BannerResponse,
    BannerUpdate,
)
from backend.app.services.content_service import (
    create_banner,
    deactivate_banner,
    get_active_banners,
    get_background,
    update_banner,
    upsert_background,
)

router = APIRouter(prefix="/content", tags=["Content"])


# Background

@router.get("/background", response_model=BackgroundResponse)
def read_background(db: Session = Depends(get_db)):
    return get_background(db)


@router.put("/background", response_model=BackgroundResponse)
def write_background(
    payload: BackgroundUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return upsert_background(db, payload)


# Banners

@router.get("/banners", response_model=list[BannerResponse])
def read_banners(db: Session = Depends(get_db)):
    return get_active_banners(db)


@router.post("/banners", response_model=BannerResponse, status_code=status.HTTP_201_CREATED)
def create_new_banner(
    payload: BannerCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return create_banner(db, payload)


@router.put("/banners/{banner_id}", response_model=BannerResponse)
def update_existing_banner(
    banner_id: UUID,
    payload: BannerUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return update_banner(db, banner_id, payload)


@router.delete("/banners/{banner_id}", response_model=BannerResponse)
def deactivate_existing_banner(
    banner_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return deactivate_banner(db, banner_id)
