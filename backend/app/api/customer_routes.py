from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_customer
from backend.app.db.deps import get_db
from backend.app.models.customer_user import CustomerUser
from backend.app.schemas.customer import CustomerMeResponse, CustomerUpdateRequest

router = APIRouter(prefix="/customer", tags=["customer"])


def _to_customer_me_response(user: CustomerUser) -> CustomerMeResponse:
    return CustomerMeResponse.model_validate(user)


@router.get("/me", response_model=CustomerMeResponse)
def get_customer_me(
    current_customer: CustomerUser = Depends(get_current_customer),
):
    return _to_customer_me_response(current_customer)


@router.patch("/me", response_model=CustomerMeResponse)
def update_customer_me(
    payload: CustomerUpdateRequest,
    db: Session = Depends(get_db),
    current_customer: CustomerUser = Depends(get_current_customer),
):
    updates = payload.model_dump(exclude_unset=True)

    if "full_name" in updates:
        current_customer.full_name = updates["full_name"]
    if "phone" in updates:
        current_customer.phone = updates["phone"]

    db.add(current_customer)
    db.commit()
    db.refresh(current_customer)

    return _to_customer_me_response(current_customer)
