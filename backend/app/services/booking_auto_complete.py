import json
import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from backend.app.models.airport import Airport
from backend.app.models.booking import Booking

logger = logging.getLogger(__name__)


def _to_utc(dt_str: str, tz_name: str) -> datetime:
    parsed = datetime.fromisoformat(dt_str)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(tz_name))
    return parsed.astimezone(timezone.utc)


def auto_complete_bookings(db: Session):
    now_utc = datetime.now(timezone.utc)
    confirmed_bookings = db.query(Booking).filter(Booking.status == "CONFIRMED").all()
    completed_count = 0

    for booking in confirmed_bookings:
        try:
            snapshot = json.loads(booking.flight_snapshot)
        except Exception:
            logger.exception(
                "Failed to parse flight_snapshot for booking %s", booking.id
            )
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
                if _to_utc(departure_time_str, airport.timezone) < now_utc:
                    booking.status = "COMPLETED"
                    booking.status_updated_at = now_utc
                    completed_count += 1
            except Exception:
                logger.exception(
                    "Failed to auto-complete one-way booking %s", booking.id
                )
                continue

        elif booking.type == "ROUND_TRIP":
            for leg_name, flag in (
                ("outbound", "outbound_completed"),
                ("inbound", "inbound_completed"),
            ):
                leg = snapshot.get(leg_name) or {}
                if getattr(booking, flag):
                    continue
                dep_str = leg.get("departure_time")
                origin = leg.get("origin")
                if not dep_str or not origin:
                    continue
                airport = db.query(Airport).filter(Airport.code == origin).first()
                if not airport:
                    continue
                try:
                    if _to_utc(dep_str, airport.timezone) < now_utc:
                        setattr(booking, flag, True)
                except Exception:
                    logger.exception(
                        "Failed to auto-complete %s leg for booking %s",
                        leg_name,
                        booking.id,
                    )
                    continue

            if booking.outbound_completed and booking.inbound_completed:
                booking.status = "COMPLETED"
                booking.status_updated_at = now_utc
                completed_count += 1

    try:
        db.commit()
    except Exception as exc:
        logger.exception("Failed to auto-complete bookings: %s", exc)
        db.rollback()
        raise

    return {"checked": len(confirmed_bookings), "completed": completed_count}
