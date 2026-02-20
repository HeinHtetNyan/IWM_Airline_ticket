import json
from typing import List
from uuid import UUID
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.deps import get_db
from app.auth.deps import get_current_customer
from app.models.booking import Booking
from app.models.customer_user import CustomerUser
from app.models.booking_passenger import BookingPassenger as Passenger

from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.passenger import PassengerBulkCreate, PassengerOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


# Create Booking
@router.post("/", response_model=BookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):

    snapshot = payload.flight_snapshot

    snapshot_price_usd = snapshot.get("final_price_usd")
    snapshot_price_mmk = snapshot.get("final_price_mmk")

    if snapshot_price_usd is None or snapshot_price_mmk is None:
        raise HTTPException(status_code=400, detail="Invalid snapshot price data")

    calculated_total_usd = round(float(snapshot_price_usd) * payload.adults, 2)
    calculated_total_mmk = round(float(snapshot_price_mmk) * payload.adults, 2)

    # Anti-spam (10 seconds)
    ten_seconds_ago = datetime.utcnow() - timedelta(seconds=10)

    existing = (
        db.query(Booking)
        .filter(
            Booking.customer_id == current_user.id,
            Booking.bundle_key == payload.bundle_key,
            Booking.status == "PROCESSING",
            Booking.created_at >= ten_seconds_ago,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Duplicate booking detected. Please wait a few seconds.",
        )

    booking = Booking(
        customer_id=current_user.id,
        type=payload.type,
        adults=payload.adults,
        bundle_key=payload.bundle_key,
        flight_snapshot=json.dumps(payload.flight_snapshot),
        final_price_usd=calculated_total_usd,
        final_price_mmk=calculated_total_mmk,
        status="PROCESSING",
        # payment_status defaults to PENDING automatically in DB
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    return BookingOut(
        booking_id=booking.id,
        booking_code=None,
        type=booking.type,
        adults=booking.adults,
        bundle_key=booking.bundle_key,
        flight_snapshot=json.loads(booking.flight_snapshot),
        final_price_usd=booking.final_price_usd,
        final_price_mmk=booking.final_price_mmk,
        status=booking.status,
        payment_status=booking.payment_status,
        created_at=booking.created_at,
        passengers=None,
    )


# Add Passengers + Generate Code
@router.post("/{booking_id}/passengers", response_model=List[PassengerOut])
def add_passengers(
    booking_id: UUID,
    payload: PassengerBulkCreate,
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
        raise HTTPException(status_code=404, detail="Booking not found")

    existing_passengers = (
        db.query(Passenger)
        .filter(Passenger.booking_id == booking_id)
        .all()
    )

    if existing_passengers:
        raise HTTPException(
            status_code=400,
            detail="Passengers already added for this booking.",
        )

    if len(payload.passengers) != booking.adults:
        raise HTTPException(
            status_code=400,
            detail=f"Passenger count must be {booking.adults}",
        )

    saved_passengers = []

    for p in payload.passengers:
        passenger = Passenger(
            booking_id=booking.id,
            given_name=p.given_name,
            last_name=p.last_name,
            passport_number=p.passport_number,
            gender=p.gender,
            date_of_birth=p.date_of_birth,
            nationality=p.nationality,
            phone_number=p.phone_number,
        )

        db.add(passenger)
        saved_passengers.append(passenger)

    db.commit()

    for p in saved_passengers:
        db.refresh(p)

    # Generate Booking Code AFTER passengers added
    if not booking.booking_code:
        current_year = datetime.utcnow().year
        booking.booking_code = f"IWM-{current_year}-{booking.booking_number:06d}"
        db.commit()
        db.refresh(booking)

    return saved_passengers


# List My Bookings
@router.get("/me", response_model=List[BookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):

    bookings = (
        db.query(Booking)
        .filter(Booking.customer_id == current_user.id)
        .order_by(Booking.created_at.desc())
        .all()
    )

    return [
        BookingOut(
            booking_id=b.id,
            booking_code=b.booking_code,
            type=b.type,
            adults=b.adults,
            bundle_key=b.bundle_key,
            flight_snapshot=json.loads(b.flight_snapshot),
            final_price_usd=b.final_price_usd,
            final_price_mmk=b.final_price_mmk,
            status=b.status,
            payment_status=b.payment_status,
            created_at=b.created_at,
            passengers=None,
        )
        for b in bookings
    ]


# Booking Detail (WITH PASSENGERS)
@router.get("/{booking_id}", response_model=BookingOut)
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

    passengers = (
        db.query(Passenger)
        .filter(Passenger.booking_id == booking_id)
        .all()
    )

    return BookingOut(
        booking_id=booking.id,
        booking_code=booking.booking_code,
        type=booking.type,
        adults=booking.adults,
        bundle_key=booking.bundle_key,
        flight_snapshot=json.loads(booking.flight_snapshot),
        final_price_usd=booking.final_price_usd,
        final_price_mmk=booking.final_price_mmk,
        status=booking.status,
        payment_status=booking.payment_status,
        created_at=booking.created_at,
        passengers=passengers,
    )
