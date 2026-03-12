from sqlalchemy.orm import Session
from uuid import UUID

from backend.app.models.admin_user import AdminUser
from backend.app.auth.security import get_password_hash


def get_staff_list(db: Session):
    return (
        db.query(AdminUser)
        .filter(
            AdminUser.role == "STAFF",
            AdminUser.is_active == True
        )
        .all()
    )


def get_all_staff(db: Session):
    return (
        db.query(AdminUser)
        .filter(AdminUser.role == "STAFF")
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
    if "password" in data:
        data["password_hash"] = get_password_hash(data.pop("password"))

    for key, value in data.items():
        if key == "role":
            continue

        setattr(staff, key, value)

    db.commit()
    db.refresh(staff)
    return staff


def delete_staff(db: Session, staff: AdminUser):
    db.delete(staff)
    db.commit()


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


def count_super_admins(db):
    return (
        db.query(AdminUser)
        .filter(
            AdminUser.role == "SUPER_ADMIN",
            AdminUser.is_active == True
        )
        .count()
    )
