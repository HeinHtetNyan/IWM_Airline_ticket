from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.booking import Booking


def auto_cancel_expired_bookings(db: Session, expire_minutes: int = 30):
    """
    - Cancel PROCESSING+PENDING bookings older than expire_minutes.
    - Auto-confirm PROCESSING+PAID bookings older than expire_minutes to avoid stuck state.
    """
    threshold_time = datetime.now(timezone.utc) - timedelta(minutes=expire_minutes)

    pending_to_cancel = (
        db.query(Booking)
        .filter(
            Booking.status == "PROCESSING",
            Booking.payment_status == "PENDING",
            Booking.created_at < threshold_time,
        )
        .all()
    )

    paid_to_confirm = (
        db.query(Booking)
        .filter(
            Booking.status == "PROCESSING",
            Booking.payment_status == "PAID",
            Booking.created_at < threshold_time,
        )
        .all()
    )

    cancelled_count = 0
    confirmed_count = 0

    for booking in pending_to_cancel:
        booking.status = "CANCELLED"
        cancelled_count += 1

    for booking in paid_to_confirm:
        booking.status = "CONFIRMED"
        confirmed_count += 1

    db.commit()

    return {
        "expired_found": len(pending_to_cancel) + len(paid_to_confirm),
        "cancelled_count": cancelled_count,
        "confirmed_count": confirmed_count,
        "expire_minutes": expire_minutes,
    }
