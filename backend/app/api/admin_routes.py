from fastapi import APIRouter, Depends, HTTPException
from app.auth.deps import require_admin
from app.schemas.flight_override import (
    FlightOverrideCreate,
    FlightOverrideResponse,
    FlightOverrideUpdate
)
from app.crud.flight_override import (
    create_override,
    get_all_overrides,
    update_override_price,
    delete_override
)
from app.db.deps import get_db
from sqlalchemy.orm import Session
from app.auth.deps import get_current_admin
from app.models.booking import Booking
from app.schemas.booking import BookingStatusUpdate
from uuid import UUID


router = APIRouter(prefix="/admin", tags=["admin"])


# Admin identity check
@router.get("/me")
def admin_me(admin=Depends(require_admin)):
    return {
        "id": str(admin.id),
        "email": admin.email,
        "name": admin.name,
        "role": admin.role,
        "is_active": admin.is_active,
    }


#Admin override
@router.post("/overrides", response_model=FlightOverrideResponse)
def create_flight_override(
    override: FlightOverrideCreate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    return create_override(db, override)


@router.get("/overrides", response_model=list[FlightOverrideResponse])
def list_flight_overrides(
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    return get_all_overrides(db)


@router.put("/overrides/{override_id}", response_model=FlightOverrideResponse)
def update_flight_override(
    override_id: str,
    payload: FlightOverrideUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    return update_override_price(db, override_id, payload.override_price_usd)


@router.delete("/overrides/{override_id}")
def delete_flight_override(
    override_id: str,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    delete_override(db, override_id)
    return {"message": "Override deleted successfully"}


#Admin Booking status
@router.get("/bookings")
def list_all_bookings(
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    bookings = db.query(Booking).order_by(Booking.created_at.desc()).all()

    return [
        {
            "booking_id": b.id,
            "customer_id": b.customer_id,
            "airline_code": b.airline_code,
            "flight_number": b.flight_number,
            "origin": b.origin,
            "destination": b.destination,
            "departure_date": b.departure_date,
            "departure_time": b.departure_time,
            "arrival_time": b.arrival_time,
            "final_price_usd": b.final_price_usd,
            "status": b.status,
            "created_at": b.created_at,
        }
        for b in bookings
    ]

@router.put("/bookings/{booking_id}")
def update_booking_status(
    booking_id: UUID,
    payload: BookingStatusUpdate,
    db: Session = Depends(get_db),
    admin = Depends(get_current_admin),
):
    booking = db.query(Booking).filter(
        Booking.id == booking_id
    ).first()

    if not booking:
        raise HTTPException(
            status_code=404,
            detail="Booking not found",
        )

    allowed_status = {
        "PROCESSING",
        "CONFIRMED",
        "REJECTED",
        "CANCELLED",
        "COMPLETED",
    }

    if payload.status not in allowed_status:
        raise HTTPException(
            status_code=400,
            detail="Invalid booking status",
        )

    booking.status = payload.status
    db.commit()
    db.refresh(booking)

    return {
        "booking_id": booking.id,
        "new_status": booking.status,
    }
