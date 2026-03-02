from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.customer_user import CustomerUser
from app.models.admin_user import AdminUser
from app.auth.tokens import decode_access_token

security = HTTPBearer()


def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CustomerUser:

    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or role != "CUSTOMER":
        raise HTTPException(status_code=401, detail="Invalid customer token")

    user = db.query(CustomerUser).filter(CustomerUser.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user

def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AdminUser:

    token = credentials.credentials
    payload = decode_access_token(token)

    admin_id = payload.get("sub")
    role = payload.get("role")

    # Allow both STAFF and SUPER_ADMIN
    if not admin_id or role not in {"STAFF", "SUPER_ADMIN"}:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()

    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin not found or inactive")

    return admin


def require_admin(
    admin: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    return admin


def require_super_admin(
    admin: AdminUser = Depends(get_current_admin),
) -> AdminUser:

    if admin.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )

    return admin
