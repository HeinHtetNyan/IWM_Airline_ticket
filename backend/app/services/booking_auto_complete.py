from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import json
from sqlalchemy.orm import Session
from backend.app.models.booking import Booking
from backend.app.models.airport import Airport


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

        departure_time_str = snapshot.get("departure_time")
        origin = snapshot.get("origin")

        if not departure_time_str or not origin:
            continue

        airport = db.query(Airport).filter(Airport.code == origin).first()
        if not airport:
            # If airport timezone unknown → skip safely
            continue

        try:
            local_naive = datetime.fromisoformat(departure_time_str)

            local_aware = local_naive.replace(
                tzinfo=ZoneInfo(airport.timezone)
            )

            departure_utc = local_aware.astimezone(timezone.utc)

        except Exception:
            continue

        if departure_utc < now_utc:
            booking.status = "COMPLETED"
            completed_count += 1

    db.commit()

    return {
        "checked": len(confirmed_bookings),
        "completed": completed_count,
    }
