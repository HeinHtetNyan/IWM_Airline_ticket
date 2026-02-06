from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict

from app.models.flight import Flight


def sync_flights_from_api(
    db: Session,
    *,
    api_flights: List[Dict],
):

    now = datetime.utcnow()
    seen_external_ids: set[str] = set()

    for data in api_flights:
        external_id = data["external_flight_id"]
        seen_external_ids.add(external_id)

        flight = (
            db.query(Flight)
            .filter(Flight.external_flight_id == external_id)
            .first()
        )

        if flight:
            # Update core data from API
            flight.airline_code = data["airline_code"]
            flight.flight_number = data["flight_number"]
            flight.origin = data["origin"]
            flight.destination = data["destination"]
            flight.departure_time = data["departure_time"]
            flight.arrival_time = data["arrival_time"]
            flight.base_price_usd = data.get("base_price_usd")

            # Availability tracking
            flight.is_available = True
            flight.last_seen_at = now

        else:
            # New flight from API
            flight = Flight(
                id=data["id"],
                external_flight_id=external_id,
                airline_code=data["airline_code"],
                flight_number=data["flight_number"],
                origin=data["origin"],
                destination=data["destination"],
                departure_time=data["departure_time"],
                arrival_time=data["arrival_time"],
                base_price_usd=data.get("base_price_usd"),
                is_available=True,
                is_published=False,
                is_visible=True,
                last_seen_at=now,
            )
            db.add(flight)

    # Mark disappeared flights
    db.query(Flight).filter(
        Flight.last_seen_at < now
    ).update(
        {"is_available": False},
        synchronize_session=False,
    )

    db.commit()
