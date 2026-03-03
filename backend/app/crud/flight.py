from datetime import datetime

from sqlalchemy.orm import Session

from app.models.flight_override import FlightOverride
from app.schemas.flight import AdminFlightUpdate


def get_flight_by_id(db: Session, flight_id: str) -> FlightOverride | None:
    return db.query(FlightOverride).filter(FlightOverride.id == flight_id).first()


def list_flights(db: Session) -> list[FlightOverride]:
    return db.query(FlightOverride).order_by(FlightOverride.departure_date).all()


def admin_update_flight(
    db: Session,
    *,
    flight: FlightOverride,
    flight_in: AdminFlightUpdate,
) -> FlightOverride:
    data = flight_in.model_dump(exclude_unset=True)

    for field, value in data.items():
        if hasattr(flight, field):
            setattr(flight, field, value)

    db.commit()
    db.refresh(flight)
    return flight


# API sync
def mark_flight_seen(db: Session, flight: FlightOverride):
    if hasattr(flight, "last_seen_at"):
        flight.last_seen_at = datetime.utcnow()
    if hasattr(flight, "is_available"):
        flight.is_available = True
    db.commit()
