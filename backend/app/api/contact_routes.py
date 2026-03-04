from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.deps import get_db
from backend.app.auth.deps import get_current_customer
from backend.app.models.customer_user import CustomerUser
from backend.app.models.customer_contact import CustomerContact
from backend.app.schemas.contact import ContactCreate, ContactOut

router = APIRouter(prefix="/contact", tags=["contact"])


# Create or Update Contact
@router.post("/", response_model=ContactOut)
def create_or_update_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):

    contact = (
        db.query(CustomerContact)
        .filter(CustomerContact.customer_id == current_user.id)
        .first()
    )

    if contact:
        # Update existing
        contact.given_name = payload.given_name
        contact.last_name = payload.last_name
        contact.email = payload.email
        contact.country_of_residence = payload.country_of_residence
        contact.phone_number = payload.phone_number
    else:
        contact = CustomerContact(
            customer_id=current_user.id,
            given_name=payload.given_name,
            last_name=payload.last_name,
            email=payload.email,
            country_of_residence=payload.country_of_residence,
            phone_number=payload.phone_number,
        )
        db.add(contact)

    db.commit()
    db.refresh(contact)

    return contact


# Get My Contact
@router.get("/me", response_model=ContactOut)
def get_my_contact(
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):

    contact = (
        db.query(CustomerContact)
        .filter(CustomerContact.customer_id == current_user.id)
        .first()
    )

    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    return contact
