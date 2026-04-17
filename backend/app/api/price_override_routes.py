from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.auth.deps import require_super_admin
from backend.app.db.deps import get_db
from backend.app.models.admin_user import AdminUser
from backend.app.schemas.price_override import (
    PriceOverrideCreate,
    PriceOverrideResponse,
)
from backend.app.services.price_override_service import (
    create_price_override,
    deactivate_price_override,
    list_price_overrides,
)

router = APIRouter(prefix="/admin/price-overrides", tags=["admin"])


@router.post("", response_model=PriceOverrideResponse)
def create_override(
    payload: PriceOverrideCreate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return create_price_override(db, payload)


@router.get("", response_model=list[PriceOverrideResponse])
def read_overrides(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return list_price_overrides(db)


@router.delete("/{override_id}")
def disable_override(
    override_id: UUID,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    override = deactivate_price_override(db, override_id)
    if override is None:
        raise HTTPException(status_code=404, detail="Price override not found")
    return {"message": "Price override disabled successfully", "id": override.id}
