import uuid
from datetime import datetime, date

from sqlalchemy import String, DateTime, ForeignKey, Float, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Booking(Base):
    __tablename__ = "bookings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    customer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("customer_users.id"),
        nullable=False
    )

    airline_code: Mapped[str] = mapped_column(String, nullable=False)
    flight_number: Mapped[str] = mapped_column(String, nullable=False)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    departure_time: Mapped[str] = mapped_column(String, nullable=False)
    arrival_time: Mapped[str] = mapped_column(String, nullable=False)

    final_price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    final_price_mmk: Mapped[float] = mapped_column(Float, nullable=False)

    status: Mapped[str] = mapped_column(
        String,
        default="PROCESSING",
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
