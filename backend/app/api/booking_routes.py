from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.auth.deps import get_current_customer
from app.models.booking import Booking
from app.models.customer_user import CustomerUser
from app.schemas.booking import BookingCreate

router = APIRouter(prefix="/bookings", tags=["bookings"])


# Booking creation
@router.post("/")
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    from datetime import datetime

    departure_date = datetime.fromisoformat(
        payload.departure_time
    ).date()

    booking = Booking(
        customer_id=current_user.id,
        airline_code=payload.airline_code,
        flight_number=payload.flight_number,
        origin=payload.origin,
        destination=payload.destination,
        departure_date=departure_date,
        departure_time=payload.departure_time,
        arrival_time=payload.arrival_time,
        final_price_usd=payload.final_price_usd,
        final_price_mmk=payload.final_price_mmk,
        status="PROCESSING",
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "airline_code": booking.airline_code,
        "flight_number": booking.flight_number,
        "origin": booking.origin,
        "destination": booking.destination,
        "departure_time": booking.departure_time,
        "arrival_time": booking.arrival_time,
        "final_price_usd": booking.final_price_usd,
        "status": booking.status,
    }


# List my bookings
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
            "airline_code": b.airline_code,
            "flight_number": b.flight_number,
            "origin": b.origin,
            "destination": b.destination,
            "departure_date": b.departure_date,
            "departure_time": b.departure_time,
            "arrival_time": b.arrival_time,
            "final_price_usd": b.final_price_usd,
            "final_price_mmk": b.final_price_mmk,
            "status": b.status,
        }
        for b in bookings
    ]


# Booking detail
@router.get("/{booking_id}")
def get_my_booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    booking = (
        db.query(Booking)
        .filter(
            Booking.id == booking_id,
            Booking.customer_id == current_user.id,
        )
        .first()
    )

    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found",
        )

    return {
        "booking_id": booking.id,
        "airline_code": booking.airline_code,
        "flight_number": booking.flight_number,
        "origin": booking.origin,
        "destination": booking.destination,
        "departure_date": booking.departure_date,
        "departure_time": booking.departure_time,
        "arrival_time": booking.arrival_time,
        "final_price_usd": booking.final_price_usd,
        "final_price_mmk": booking.final_price_mmk,
        "status": booking.status,
    }

