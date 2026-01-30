from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.models.customer_user import CustomerUser
from app.models.admin_user import AdminUser
from app.auth.tokens import decode_access_token

# Swagger "Authorize" buttons:
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/customer/token")
oauth2_admin_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/admin/token")


def get_current_customer(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> CustomerUser:
    payload = decode_access_token(token)

    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or role != "CUSTOMER":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer token",
        )

    user = db.query(CustomerUser).filter(CustomerUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return user


def get_current_admin(
    token: str = Depends(oauth2_admin_scheme),
    db: Session = Depends(get_db),
) -> AdminUser:
    payload = decode_access_token(token)

    admin_id = payload.get("sub")
    role = payload.get("role")

    if not admin_id or role != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin token",
        )

    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin not found or inactive",
        )

    return admin

require_admin = get_current_admin

def require_super_admin(
    admin: AdminUser = Depends(get_current_admin),
) -> AdminUser:
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin only",
        )
    return admin
