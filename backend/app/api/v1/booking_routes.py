from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
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
        customer_id=current_user.id,
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


@router.get("/me")
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    bookings = (
        db.query(Booking)
        .filter(Booking.customer_id == current_user.id)
        .order_by(Booking.id.desc())
        .all()
    )

    return [
        {
            "booking_id": b.id,
            "customer_id": b.customer_id,
            "status": b.status,
        }
        for b in bookings
    ]


@router.get("/{booking_id}")
def get_my_booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.customer_id == current_user.id)
        .first()
    )

    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    return {
        "booking_id": booking.id,
        "customer_id": booking.customer_id,
        "status": booking.status,
    }
