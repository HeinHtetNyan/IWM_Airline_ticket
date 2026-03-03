import json
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.deps import get_current_customer
from app.db.deps import get_db
from app.models.booking import Booking
from app.models.booking_passenger import BookingPassenger as Passenger
from app.models.customer_user import CustomerUser
from app.models.exchange_rate import ExchangeRate
from app.models.flight_override import FlightOverride

from app.schemas.booking import BookingCreate, BookingOut
from app.schemas.passenger import PassengerBulkCreate, PassengerOut

router = APIRouter(prefix="/bookings", tags=["bookings"])

MONEY_QUANT = Decimal("0.01")
GLOBAL_MARKUP_PERCENT = Decimal("15")


def _to_decimal(value: object, field_name: str) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail=f"Invalid {field_name}")

    if amount <= 0:
        raise HTTPException(status_code=400, detail=f"{field_name} must be greater than 0")

    return amount


def _round_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT, rounding=ROUND_HALF_UP)


def _require_exchange_rate(db: Session) -> Decimal:
    exchange = db.query(ExchangeRate).filter(ExchangeRate.id == 1).first()
    if not exchange or exchange.usd_to_mmk <= 0:
        raise HTTPException(status_code=500, detail="System exchange rate is not configured")
    return Decimal(str(exchange.usd_to_mmk))


def _validate_snapshot_shape(booking_type: str, snapshot: dict):
    if booking_type == "ONE_WAY":
        required_fields = ("departure_time", "origin", "destination", "airline_code", "flight_number")
        missing = [field for field in required_fields if not snapshot.get(field)]
        if missing:
            raise HTTPException(status_code=400, detail=f"flight_snapshot missing fields: {missing}")
        if "outbound" in snapshot or "inbound" in snapshot:
            raise HTTPException(status_code=400, detail="ONE_WAY booking cannot include outbound/inbound snapshot")
    elif booking_type == "ROUND_TRIP":
        outbound = snapshot.get("outbound")
        inbound = snapshot.get("inbound")
        if not isinstance(outbound, dict) or not isinstance(inbound, dict):
            raise HTTPException(status_code=400, detail="ROUND_TRIP snapshot must include outbound and inbound")

        for leg_name, leg in (("outbound", outbound), ("inbound", inbound)):
            required_fields = ("departure_time", "origin", "destination", "airline_code", "flight_number")
            missing = [field for field in required_fields if not leg.get(field)]
            if missing:
                raise HTTPException(status_code=400, detail=f"{leg_name} missing fields: {missing}")
    else:
        raise HTTPException(status_code=400, detail="Invalid booking type")


def _one_way_price_per_adult_usd(db: Session, snapshot: dict) -> Decimal:
    base_price = _to_decimal(snapshot.get("base_price_usd"), "base_price_usd")
    system_price = base_price * (Decimal("1") + (GLOBAL_MARKUP_PERCENT / Decimal("100")))

    departure_time = snapshot.get("departure_time")
    if not isinstance(departure_time, str):
        raise HTTPException(status_code=400, detail="Invalid departure_time")

    try:
        departure_date = datetime.fromisoformat(departure_time).date()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid departure_time format")

    override = (
        db.query(FlightOverride)
        .filter(
            FlightOverride.airline_code == snapshot.get("airline_code"),
            FlightOverride.flight_number == snapshot.get("flight_number"),
            FlightOverride.departure_date == departure_date,
        )
        .first()
    )

    if override and override.override_price_usd is not None:
        override_price = Decimal(str(override.override_price_usd))
        system_price = max(system_price, override_price)

    return _round_money(system_price)


def _round_trip_price_per_adult_usd(snapshot: dict) -> Decimal:
    base_price = _to_decimal(snapshot.get("base_price_usd"), "base_price_usd")
    system_price = base_price * (Decimal("1") + (GLOBAL_MARKUP_PERCENT / Decimal("100")))
    return _round_money(system_price)


def _calculate_server_totals(db: Session, payload: BookingCreate) -> tuple[Decimal, Decimal]:
    _validate_snapshot_shape(payload.type, payload.flight_snapshot)

    usd_to_mmk = _require_exchange_rate(db)

    if payload.type == "ONE_WAY":
        per_adult = _one_way_price_per_adult_usd(db, payload.flight_snapshot)
    else:
        per_adult = _round_trip_price_per_adult_usd(payload.flight_snapshot)

    total_usd = _round_money(per_adult * Decimal(payload.adults))
    total_mmk = _round_money(total_usd * usd_to_mmk)
    return total_usd, total_mmk


def _booking_duplicate_filter(db: Session, current_user: CustomerUser, payload: BookingCreate):
    ten_seconds_ago = datetime.utcnow() - timedelta(seconds=10)

    query = db.query(Booking).filter(
        Booking.customer_id == current_user.id,
        Booking.status == "PROCESSING",
        Booking.type == payload.type,
        Booking.adults == payload.adults,
        Booking.created_at >= ten_seconds_ago,
    )

    if payload.bundle_key:
        query = query.filter(Booking.bundle_key == payload.bundle_key)
    else:
        query = query.filter(Booking.flight_snapshot == json.dumps(payload.flight_snapshot, sort_keys=True))

    return query.first()


# Create Booking
@router.post("/", response_model=BookingOut)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: CustomerUser = Depends(get_current_customer),
):
    calculated_total_usd, calculated_total_mmk = _calculate_server_totals(db, payload)

    existing = _booking_duplicate_filter(db, current_user, payload)
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
        flight_snapshot=json.dumps(payload.flight_snapshot, sort_keys=True),
        final_price_usd=float(calculated_total_usd),
        final_price_mmk=float(calculated_total_mmk),
        status="PROCESSING",
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

    if booking.status != "PROCESSING":
        raise HTTPException(status_code=400, detail="Passengers can only be added to PROCESSING bookings")

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

    if not booking.booking_number:
        raise HTTPException(status_code=500, detail="Booking number missing")

    if not booking.booking_code:
        current_year = datetime.utcnow().year
        booking.booking_code = f"IWM-{current_year}-{booking.booking_number:06d}"

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

    try:
        db.commit()
    except IntegrityError:
        db.rollback()

        booking = (
            db.query(Booking)
            .filter(Booking.id == booking_id, Booking.customer_id == current_user.id)
            .first()
        )
        if not booking:
            raise HTTPException(status_code=404, detail="Booking not found")

        booking.booking_code = f"IWM-{datetime.utcnow().year}-{booking.booking_number:06d}-{booking.id.hex[:6].upper()}"

        db.query(Passenger).filter(Passenger.booking_id == booking_id).delete()
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
