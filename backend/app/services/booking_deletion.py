import logging
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.app.models.admin_user import AdminUser
from backend.app.models.booking import Booking
from backend.app.models.booking_deletion_log import BookingDeletionLog

logger = logging.getLogger(__name__)


def _create_deletion_log(
    db: Session,
    booking_id: UUID,
    deleted_by: str,
    deleted_role: str,
    reason: str,
) -> None:
    db.add(
        BookingDeletionLog(
            booking_id=booking_id,
            deleted_by=deleted_by,
            deleted_role=deleted_role,
            reason=reason,
        )
    )
    db.flush()


def delete_cancelled_booking_by_admin(
    db: Session,
    booking_id: UUID,
    admin: AdminUser,
) -> dict:
    booking = (
        db.query(Booking)
        .filter(Booking.id == booking_id)
        .with_for_update()
        .first()
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    if booking.status != "CANCELLED":
        raise HTTPException(status_code=400, detail="Only cancelled bookings can be deleted")

    try:
        _create_deletion_log(
            db=db,
            booking_id=booking.id,
            deleted_by=str(admin.id),
            deleted_role=admin.role,
            reason="manual_delete",
        )
        db.delete(booking)
        db.commit()
    except HTTPException:
        raise
    except Exception:
        db.rollback()
        raise

    return {
        "booking_id": booking_id,
        "deleted_by": {
            "id": str(admin.id),
            "email": admin.email,
        },
        "reason": "manual_delete",
    }


def auto_delete_expired_cancelled_bookings(
    db: Session,
    delete_days: int,
    batch_size: int = 100,
) -> dict:
    threshold_time = datetime.now(timezone.utc) - timedelta(days=delete_days)
    expired_found = 0
    deleted_count = 0

    try:
        while True:
            expired_bookings = (
                db.query(Booking)
                .filter(
                    Booking.status == "CANCELLED",
                    func.coalesce(Booking.status_updated_at, Booking.created_at) <= threshold_time,
                )
                .order_by(func.coalesce(Booking.status_updated_at, Booking.created_at).asc())
                .limit(batch_size)
                .all()
            )

            if not expired_bookings:
                break

            expired_found += len(expired_bookings)

            for booking in expired_bookings:
                _create_deletion_log(
                    db=db,
                    booking_id=booking.id,
                    deleted_by="system",
                    deleted_role="SYSTEM",
                    reason="auto_delete",
                )
                db.delete(booking)
                deleted_count += 1

            db.commit()
    except Exception as exc:
        logger.exception("Failed to auto-delete cancelled bookings: %s", exc)
        db.rollback()
        raise

    return {
        "expired_found": expired_found,
        "deleted_count": deleted_count,
        "delete_days": delete_days,
    }
