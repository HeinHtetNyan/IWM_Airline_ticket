from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.customer_user import CustomerUser


def get_customers(db: Session):
    return (
        db.query(CustomerUser)
        .order_by(CustomerUser.created_at.desc())
        .all()
    )


def get_customer(db: Session, customer_id: UUID):
    return (
        db.query(CustomerUser)
        .filter(CustomerUser.id == customer_id)
        .first()
    )


def update_customer(db: Session, customer: CustomerUser, data: dict):
    allowed_fields = {"full_name", "phone"}

    for key, value in data.items():
        if key not in allowed_fields:
            continue

        setattr(customer, key, value)

    db.commit()
    db.refresh(customer)
    return customer


def deactivate_customer(db: Session, customer: CustomerUser):
    customer.is_active = False
    db.commit()
    db.refresh(customer)
    return customer


def activate_customer(db: Session, customer: CustomerUser):
    customer.is_active = True
    db.commit()
    db.refresh(customer)
    return customer
