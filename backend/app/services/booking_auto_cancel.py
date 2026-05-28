from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from backend.app.models.booking import Booking


def auto_cancel_expired_bookings(db: Session, expire_minutes: int = 30):
    """
    Cancel PROCESSING bookings older than expire_minutes
    ONLY if payment_status is still PENDING.
    """

    threshold_time = datetime.now(timezone.utc) - timedelta(minutes=expire_minutes)
    now = datetime.now(timezone.utc)

    expired_bookings = (
        db.query(Booking)
        .filter(
            Booking.status == "PROCESSING",
            Booking.payment_status == "PENDING",
            Booking.created_at < threshold_time,
        )
        .all()
    )

    cancelled_count = 0

    for booking in expired_bookings:
        booking.status = "CANCELLED"
        booking.status_updated_at = now
        cancelled_count += 1

    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "expired_found": len(expired_bookings),
        "cancelled_count": cancelled_count,
        "expire_minutes": expire_minutes,
    }
