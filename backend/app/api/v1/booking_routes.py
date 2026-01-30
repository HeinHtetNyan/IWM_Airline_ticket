from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.auth.deps import get_current_customer
from app.models.booking import Booking
from app.models.customer_user import CustomerUser

router = APIRouter(prefix="/bookings", tags=["bookings"])

@router.post("/")
def create_booking(
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    booking = Booking(
        customer_id=current_user.id,  # 👈 THIS IS THE LINE YOU ASKED ABOUT
        status="PROCESSING",
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "customer_id": booking.customer_id,
        "status": booking.status,
    }
