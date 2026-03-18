from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.models.customer_contact import CustomerContact
from backend.app.schemas.contact import ContactCreate, ContactUpdate


def get_contact_by_customer_id(
    db: Session,
    customer_id: UUID,
    *,
    for_update: bool = False,
) -> CustomerContact | None:
    query = db.query(CustomerContact).filter(CustomerContact.customer_id == customer_id)
    if for_update:
        query = query.with_for_update()
    return query.first()


def get_my_contact_or_404(db: Session, customer_id: UUID) -> CustomerContact:
    contact = get_contact_by_customer_id(db, customer_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


def create_my_contact(
    db: Session,
    customer_id: UUID,
    payload: ContactCreate,
) -> CustomerContact:
    existing_contact = get_contact_by_customer_id(db, customer_id, for_update=True)
    if existing_contact:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact already exists. Use PUT /contact/me to update.",
        )

    contact = CustomerContact(customer_id=customer_id, **payload.model_dump())
    db.add(contact)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Contact already exists. Use PUT /contact/me to update.",
        )

    db.refresh(contact)
    return contact


def update_my_contact(
    db: Session,
    customer_id: UUID,
    payload: ContactUpdate,
) -> CustomerContact:
    contact = get_contact_by_customer_id(db, customer_id, for_update=True)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    for field, value in payload.model_dump().items():
        setattr(contact, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Unable to update contact due to a conflicting record",
        )

    db.refresh(contact)
    return contact
