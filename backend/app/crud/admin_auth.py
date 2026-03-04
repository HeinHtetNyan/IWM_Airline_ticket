from sqlalchemy.orm import Session

from app.models.admin_user import AdminUser
from app.auth.security import get_password_hash, verify_password


def get_admin_by_email(db: Session, email: str) -> AdminUser | None:
    normalized_email = email.strip().lower()
    return db.query(AdminUser).filter(AdminUser.email == normalized_email).first()


def create_admin(
    db: Session,
    name: str,
    email: str,
    password: str,
    role: str = "STAFF",
) -> AdminUser:
    normalized_email = email.strip().lower()
    admin = AdminUser(
        name=name,
        email=normalized_email,
        password_hash=get_password_hash(password),
        role=role,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def authenticate_admin(db: Session, email: str, password: str) -> AdminUser | None:
    admin = get_admin_by_email(db, email)
    if not admin or not admin.is_active:
        return None
    if not verify_password(password, admin.password_hash):
        return None
    return admin
