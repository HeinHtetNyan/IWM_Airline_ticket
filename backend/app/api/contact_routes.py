from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_customer
from backend.app.db.deps import get_db
from backend.app.models.customer_user import CustomerUser
from backend.app.schemas.contact import ContactCreate, ContactOut, ContactUpdate
from backend.app.services.contact_service import (
    create_my_contact,
    get_my_contact_or_404,
    update_my_contact,
)

router = APIRouter(prefix="/contact", tags=["contact"])


@router.post("/", response_model=ContactOut, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    return create_my_contact(db, current_user.id, payload)


@router.get("/me", response_model=ContactOut)
def get_my_contact(
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    return get_my_contact_or_404(db, current_user.id)


@router.put("/me", response_model=ContactOut)
def update_my_contact_route(
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    return update_my_contact(db, current_user.id, payload)
