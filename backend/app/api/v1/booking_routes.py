from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.auth.deps import get_current_customer
from app.models.booking import Booking
from app.models.customer_user import CustomerUser
from app.models.flight import Flight

from app.schemas.flight import UserFlightOut
from app.services.external_flight_api import fetch_flights_from_external_api
from app.crud.flight_sync import sync_flights_from_api

router = APIRouter(prefix="/bookings", tags=["bookings"])


# User flight search
@router.get("/search", response_model=List[UserFlightOut])
def search_flights(
    origin: str,
    destination: str,
    departure_date: str,
    db: Session = Depends(get_db),
):
    # Call external flight API
    api_flights = fetch_flights_from_external_api(
        origin=origin,
        destination=destination,
        departure_date=departure_date,
    )

    # ync API flights into DB
    sync_flights_from_api(db, api_flights=api_flights)

    # Apply admin filters
    flights = (
        db.query(Flight)
        .filter(
            Flight.origin == origin,
            Flight.destination == destination,
            Flight.is_published == True,
            Flight.is_visible == True,
            Flight.is_available == True,
        )
        .order_by(Flight.departure_time)
        .all()
    )

    return flights


# Booking creation
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
            "customer_id": b.customer_id,
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
        "customer_id": booking.customer_id,
        "status": booking.status,
    }
