from fastapi import APIRouter, Depends

from app.auth.deps import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/me")
def admin_me(admin=Depends(require_admin)):
    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "is_active": admin.is_active,
    }
