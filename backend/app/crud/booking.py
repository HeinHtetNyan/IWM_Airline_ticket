from typing import List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from backend.app.models.booking import Booking


def get_bookings_by_customer_id(db: Session, customer_id: UUID) -> List[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.customer_id == customer_id)
        .order_by(Booking.created_at.desc() if hasattr(Booking, "created_at") else Booking.id.desc())
        .all()
    )


def get_booking_by_id_for_customer(db: Session, booking_id: UUID, customer_id: UUID) -> Optional[Booking]:
    return (
        db.query(Booking)
        .filter(Booking.booking_id == booking_id, Booking.customer_id == customer_id)
        .first()
    )
