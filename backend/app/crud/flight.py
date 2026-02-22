from sqlalchemy.orm import Session
from datetime import datetime

from backend.app.models.flight import Flight
from backend.app.schemas.flight import AdminFlightUpdate


def get_flight_by_id(db: Session, flight_id: str) -> Flight | None:
    return db.query(Flight).filter(Flight.id == flight_id).first()


def list_flights(db: Session) -> list[Flight]:
    return db.query(Flight).order_by(Flight.departure_time).all()


def admin_update_flight(
    db: Session,
    *,
    flight: Flight,
    flight_in: AdminFlightUpdate,
) -> Flight:
    data = flight_in.model_dump(exclude_unset=True)

    for field, value in data.items():
        setattr(flight, field, value)

    db.commit()
    db.refresh(flight)
    return flight


# API sync
def mark_flight_seen(db: Session, flight: Flight):
    flight.last_seen_at = datetime.utcnow()
    flight.is_available = True
    db.commit()
