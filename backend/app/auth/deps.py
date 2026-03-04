from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth.tokens import TokenExpiredError, decode_access_token
from app.db.deps import get_db
from app.models.admin_user import AdminUser
from app.models.customer_user import CustomerUser

security = HTTPBearer()
optional_security = HTTPBearer(auto_error=False)


def _decode_or_401(token: str):
    try:
        return decode_access_token(token)
    except TokenExpiredError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_customer(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> CustomerUser:
    payload = _decode_or_401(credentials.credentials)
    user_id = payload.get("sub")
    role = payload.get("role")

    if not user_id or role != "CUSTOMER":
        raise HTTPException(status_code=401, detail="Invalid customer token")

    user = db.query(CustomerUser).filter(CustomerUser.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


def _load_admin_from_credentials(
    credentials: HTTPAuthorizationCredentials,
    db: Session,
) -> AdminUser:
    payload = _decode_or_401(credentials.credentials)
    admin_id = payload.get("sub")
    role = payload.get("role")

    if not admin_id or role not in {"STAFF", "SUPER_ADMIN"}:
        raise HTTPException(status_code=401, detail="Invalid admin token")

    admin = db.query(AdminUser).filter(AdminUser.id == admin_id).first()
    if not admin or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin not found or inactive")
    return admin


def get_current_admin(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> AdminUser:
    return _load_admin_from_credentials(credentials, db)


def get_current_admin_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(optional_security),
    db: Session = Depends(get_db),
) -> AdminUser | None:
    if credentials is None:
        return None
    return _load_admin_from_credentials(credentials, db)


def require_admin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    return admin


def require_super_admin(admin: AdminUser = Depends(get_current_admin)) -> AdminUser:
    if admin.role != "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin privileges required",
        )
    return admin
