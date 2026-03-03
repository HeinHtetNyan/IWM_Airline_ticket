import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models.airport import Airport
from app.models.booking import Booking


def _to_utc(departure_time_str: str, airport_tz: str):
    parsed = datetime.fromisoformat(departure_time_str)

    if parsed.tzinfo is None:
        local_aware = parsed.replace(tzinfo=ZoneInfo(airport_tz))
    else:
        local_aware = parsed

    return local_aware.astimezone(timezone.utc)


def auto_complete_bookings(db: Session):
    now_utc = datetime.now(timezone.utc)

    confirmed_bookings = (
        db.query(Booking)
        .filter(Booking.status == "CONFIRMED")
        .all()
    )

    completed_count = 0

    for booking in confirmed_bookings:
        try:
            snapshot = json.loads(booking.flight_snapshot)
        except Exception:
            continue

        if booking.type == "ONE_WAY":
            departure_time_str = snapshot.get("departure_time")
            origin = snapshot.get("origin")

            if not departure_time_str or not origin:
                continue

            airport = db.query(Airport).filter(Airport.code == origin).first()
            if not airport:
                continue

            try:
                departure_utc = _to_utc(departure_time_str, airport.timezone)
            except Exception:
                continue

            if departure_utc < now_utc:
                booking.status = "COMPLETED"
                completed_count += 1

        elif booking.type == "ROUND_TRIP":
            outbound = snapshot.get("outbound")

            if outbound and not booking.outbound_completed:
                dep_str = outbound.get("departure_time")
                origin = outbound.get("origin")

                if dep_str and origin:
                    airport = db.query(Airport).filter(Airport.code == origin).first()
                    if airport:
                        try:
                            departure_utc = _to_utc(dep_str, airport.timezone)
                            if departure_utc < now_utc:
                                booking.outbound_completed = True
                        except Exception:
                            pass

            inbound = snapshot.get("inbound")

            if inbound and not booking.inbound_completed:
                dep_str = inbound.get("departure_time")
                origin = inbound.get("origin")

                if dep_str and origin:
                    airport = db.query(Airport).filter(Airport.code == origin).first()
                    if airport:
                        try:
                            departure_utc = _to_utc(dep_str, airport.timezone)
                            if departure_utc < now_utc:
                                booking.inbound_completed = True
                        except Exception:
                            pass

            if booking.outbound_completed and booking.inbound_completed:
                booking.status = "COMPLETED"
                completed_count += 1

    db.commit()

    return {
        "checked": len(confirmed_bookings),
        "completed": completed_count,
    }
