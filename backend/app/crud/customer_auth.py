from sqlalchemy import func
from sqlalchemy.orm import Session
from backend.app.models.customer_user import CustomerUser
from backend.app.auth.security import get_password_hash, verify_password

def get_customer_by_email(db: Session, email: str) -> CustomerUser | None:
    normalized_email = email.lower().strip()
    return (
        db.query(CustomerUser)
        .filter(func.lower(CustomerUser.email) == normalized_email)
        .first()
    )

def create_customer(
    db: Session,
    *,
    email: str,
    password: str,
    full_name: str | None = None,
    phone: str | None = None,
) -> CustomerUser:
    normalized_email = email.lower().strip()
    user = CustomerUser(
        email=normalized_email,
        password_hash=get_password_hash(password),
        full_name=full_name,
        phone=phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

def authenticate_customer(db: Session, *, email: str, password: str) -> CustomerUser | None:
    normalized_email = email.lower().strip()
    user = get_customer_by_email(db, normalized_email)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user
