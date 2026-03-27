import json
from datetime import datetime, time, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.auth.deps import get_current_customer
from backend.app.db.deps import get_db
from backend.app.models.booking import Booking
from backend.app.models.booking_passenger import BookingPassenger as Passenger
from backend.app.models.customer_user import CustomerUser
from backend.app.schemas.booking import BookingCreate, CustomerBookingOut
from backend.app.schemas.passenger import PassengerBulkCreate, PassengerOut
from backend.app.services.pricing_engine import calculate_booking_totals

router = APIRouter(prefix="/bookings", tags=["bookings"])
_DUPLICATE_BOOKING_WINDOW_SECONDS = 10


def _safe_load_flight_snapshot(snapshot: str | None) -> dict:
    try:
        return json.loads(snapshot)
    except (json.JSONDecodeError, TypeError):
        return {}


def _canonical_snapshot(snapshot: dict) -> str:
    return json.dumps(snapshot, sort_keys=True, separators=(",", ":"))


def _require_non_empty_str(data: dict, field: str, errors: list[str], *, prefix: str = "") -> None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")


def _require_numeric(data: dict, field: str, errors: list[str], *, prefix: str = "") -> None:
    value = data.get(field)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        errors.append(f"{prefix}{field} must be a valid number")
        return
    if value <= 0:
        errors.append(f"{prefix}{field} must be greater than 0")


def _require_iso_datetime(data: dict, field: str, errors: list[str], *, prefix: str = "") -> None:
    value = data.get(field)
    if not isinstance(value, str) or not value.strip():
        errors.append(f"{prefix}{field} must be a non-empty string")
        return
    try:
        datetime.fromisoformat(value)
    except (ValueError, TypeError):
        errors.append(f"{prefix}{field} must be a valid ISO datetime (e.g. 2025-06-01T10:00:00)")


def _validate_snapshot(payload: BookingCreate) -> dict:
    snapshot = payload.flight_snapshot
    if not isinstance(snapshot, dict):
        raise HTTPException(status_code=400, detail="flight_snapshot must be a JSON object")

    errors: list[str] = []
    _require_numeric(snapshot, "base_price_usd", errors)

    if payload.type == "ONE_WAY":
        _require_iso_datetime(snapshot, "departure_time", errors)
        for field in ("origin", "destination"):
            _require_non_empty_str(snapshot, field, errors)
    else:
        for leg_name in ("outbound", "inbound"):
            leg = snapshot.get(leg_name)
            if not isinstance(leg, dict):
                errors.append(f"{leg_name} must be an object")
                continue
            _require_iso_datetime(leg, "departure_time", errors, prefix=f"{leg_name}.")
            for field in ("origin", "destination"):
                _require_non_empty_str(leg, field, errors, prefix=f"{leg_name}.")

    if errors:
        raise HTTPException(status_code=400, detail=f"Invalid flight_snapshot: {', '.join(errors)}")

    return snapshot


@router.post("/", response_model=CustomerBookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    start_time = time.time()
    snapshot = _validate_snapshot(payload)
    snapshot.setdefault("airline_code", payload.airline_code)
    snapshot.setdefault("flight_number", payload.flight_number)

    # Always recalculate pricing on the server from trusted pricing rules.
    calculated = calculate_booking_totals(db, snapshot, payload.adults, payload.type)

    snapshot["base_price_usd"] = float(calculated["base_price_usd"])
    snapshot["final_price_usd"] = float(calculated["final_price_usd"])
    snapshot["final_price_mmk"] = float(calculated["final_price_mmk"])
    canonical_snapshot = _canonical_snapshot(snapshot)

    calculated_total_usd = calculated["final_price_usd"]
    calculated_total_mmk = calculated["final_price_mmk"]

    duplicate_cutoff = datetime.now(timezone.utc) - timedelta(seconds=_DUPLICATE_BOOKING_WINDOW_SECONDS)
    duplicate_filters = [
        Booking.customer_id == current_user.id,
        Booking.status == "PROCESSING",
        Booking.created_at >= duplicate_cutoff,
        Booking.type == payload.type,
        Booking.adults == payload.adults,
        Booking.flight_snapshot == canonical_snapshot,
    ]
    if payload.bundle_key:
        duplicate_filters.append(Booking.bundle_key == payload.bundle_key)

    existing = db.query(Booking).filter(*duplicate_filters).first()
    if existing:
        raise HTTPException(status_code=400, detail="Duplicate booking detected. Please wait a few seconds.")

    booking = Booking(
        customer_id=current_user.id,
        type=payload.type,
        adults=payload.adults,
        bundle_key=payload.bundle_key,
        flight_snapshot=canonical_snapshot,
        final_price_usd=calculated_total_usd,
        final_price_mmk=calculated_total_mmk,
        status="PROCESSING",
    )

    db.add(booking)
    db.commit()
    db.refresh(booking)

    # Record booking metrics
    bookings_created_total.inc()
    booking_duration_seconds.observe(time.time() - start_time)
    
    return CustomerBookingOut(
        booking_id=booking.id,
        booking_code=None,
        type=booking.type,
        adults=booking.adults,
        bundle_key=booking.bundle_key,
        flight_snapshot=_safe_load_flight_snapshot(booking.flight_snapshot),
        final_price_usd=float(booking.final_price_usd),
        final_price_mmk=float(booking.final_price_mmk),
        status=booking.status,
        payment_status=booking.payment_status,
        ticket_url=None,
        created_at=booking.created_at,
        passengers=None,
    )


@router.post("/{booking_id}/passengers", response_model=List[PassengerOut])
def add_passengers(
    booking_id: UUID,
    payload: PassengerBulkCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id, Booking.customer_id == current_user.id)
        .with_for_update()
        .first()
    )
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status in {"CANCELLED", "COMPLETED"}:
        raise HTTPException(status_code=400, detail="Cannot add passengers to this booking status")

    if db.query(Passenger).filter(Passenger.booking_id == booking_id).first():
        raise HTTPException(status_code=400, detail="Passengers already added for this booking.")

    if len(payload.passengers) != booking.adults:
        raise HTTPException(status_code=400, detail=f"Passenger count must be {booking.adults}")

    for p in payload.passengers:
        db.add(
            Passenger(
                booking_id=booking.id,
                given_name=p.given_name,
                last_name=p.last_name,
                passport_number=p.passport_number,
                gender=p.gender,
                date_of_birth=p.date_of_birth,
                nationality=p.nationality,
                phone_number=p.phone_number,
            )
        )

    if not booking.booking_code:
        if booking.booking_number is None:
            raise HTTPException(status_code=500, detail="Booking number missing")
        current_year = datetime.now(timezone.utc).year
        booking.booking_code = f"IWM-{current_year}-{int(booking.booking_number):06d}"

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Concurrent update detected. Please retry.")

    return db.query(Passenger).filter(Passenger.booking_id == booking_id).all()


@router.get("/me", response_model=List[CustomerBookingOut])
def list_my_bookings(
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    bookings = db.query(Booking).filter(Booking.customer_id == current_user.id).order_by(Booking.created_at.desc()).all()

    return [
        CustomerBookingOut(
            booking_id=b.id,
            booking_code=b.booking_code,
            type=b.type,
            adults=b.adults,
            bundle_key=b.bundle_key,
            flight_snapshot=_safe_load_flight_snapshot(b.flight_snapshot),
            final_price_usd=float(b.final_price_usd),
            final_price_mmk=float(b.final_price_mmk),
            status=b.status,
            payment_status=b.payment_status,
            ticket_url=b.ticket_file_url if b.status == "CONFIRMED" else None,
            created_at=b.created_at,
            passengers=None,
        )
        for b in bookings
    ]


@router.get("/{booking_id}", response_model=CustomerBookingOut)
def get_my_booking_detail(
    booking_id: UUID,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    booking = db.query(Booking).filter(Booking.id == booking_id, Booking.customer_id == current_user.id).first()

    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    passengers = db.query(Passenger).filter(Passenger.booking_id == booking_id).all()

    return CustomerBookingOut(
        booking_id=booking.id,
        booking_code=booking.booking_code,
        type=booking.type,
        adults=booking.adults,
        bundle_key=booking.bundle_key,
        flight_snapshot=_safe_load_flight_snapshot(booking.flight_snapshot),
        final_price_usd=float(booking.final_price_usd),
        final_price_mmk=float(booking.final_price_mmk),
        status=booking.status,
        payment_status=booking.payment_status,
        ticket_url=booking.ticket_file_url if booking.status == "CONFIRMED" else None,
        created_at=booking.created_at,
        passengers=passengers,
    )
