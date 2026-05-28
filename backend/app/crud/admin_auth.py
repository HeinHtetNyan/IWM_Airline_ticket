from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from backend.app.models.admin_user import AdminUser
from backend.app.auth.security import get_password_hash, verify_password


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
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already registered")
    db.refresh(admin)
    return admin


def authenticate_admin(db: Session, email: str, password: str) -> AdminUser | None:
    admin = get_admin_by_email(db, email)

    # Email not found
    if not admin:
        return None

    # Account is deactivated
    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your account has been deactivated. Please contact the administrator.",
        )

    # Password incorrect
    if not verify_password(password, admin.password_hash):
        return None

    return admin
