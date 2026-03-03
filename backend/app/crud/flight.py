"""Legacy flight CRUD placeholders.

The project currently sources flights from external APIs and does not persist a Flight ORM model.
These helpers are kept to avoid import-time crashes in any legacy paths.
"""

from datetime import datetime, timezone
from typing import Any


def get_flight_by_id(db: Any, flight_id: str):
    return None


def list_flights(db: Any):
    return []


def admin_update_flight(db: Any, *, flight: Any, flight_in: Any):
    data = flight_in.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(flight, field, value)
    db.commit()
    db.refresh(flight)
    return flight


def mark_flight_seen(db: Any, flight: Any):
    flight.last_seen_at = datetime.now(timezone.utc)
    flight.is_available = True
    db.commit()
