from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException
from uuid import UUID

from backend.app.models.admin_user import AdminUser
from backend.app.auth.security import get_password_hash


def get_staff_list(db: Session):
    return (
        db.query(AdminUser)
        .filter(
            AdminUser.role == "STAFF",
        )
        .order_by(AdminUser.is_active.desc())
        .all()
    )


def get_staff(db: Session, staff_id: UUID):
    return (
        db.query(AdminUser)
        .filter(
            AdminUser.id == staff_id,
            AdminUser.role == "STAFF",
        )
        .first()
    )



def update_staff(db: Session, staff: AdminUser, data: dict):
    if "email" in data and data["email"] is not None:
        data["email"] = str(data["email"]).strip().lower()

    if "password" in data:
        data["password_hash"] = get_password_hash(data.pop("password"))

    for key, value in data.items():
        if key == "role":
            continue

        setattr(staff, key, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Email already registered")
    db.refresh(staff)
    return staff


def deactivate_staff(db: Session, staff: AdminUser):
    staff.is_active = False
    db.commit()
    db.refresh(staff)
    return staff


def activate_staff(db: Session, staff: AdminUser):
    staff.is_active = True
    db.commit()
    db.refresh(staff)
    return staff
