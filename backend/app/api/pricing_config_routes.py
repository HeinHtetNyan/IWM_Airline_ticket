from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.deps import require_admin, require_super_admin
from backend.app.db.deps import get_db
from backend.app.models.admin_user import AdminUser
from backend.app.schemas.pricing_config import (
    PricingConfigResponse,
    PricingConfigUpdate,
)
from backend.app.services.pricing_config_service import (
    get_pricing_config,
    update_global_markup,
)

router = APIRouter(prefix="/admin/pricing-config", tags=["admin"])


@router.get("", response_model=PricingConfigResponse)
def read_pricing_config(
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_admin),
):
    return get_pricing_config(db)


@router.put("", response_model=PricingConfigResponse)
def update_pricing_config(
    payload: PricingConfigUpdate,
    db: Session = Depends(get_db),
    admin: AdminUser = Depends(require_super_admin),
):
    return update_global_markup(db, payload.global_markup_percentage)
