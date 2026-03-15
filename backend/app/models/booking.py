import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    Sequence,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from backend.app.db.base import Base

booking_number_seq = Sequence("booking_number_seq", metadata=Base.metadata)


class Booking(Base):
    __tablename__ = "bookings"

    __table_args__ = (
        UniqueConstraint("booking_number", name="uq_booking_number"),
        UniqueConstraint("booking_code", name="uq_booking_code"),
        CheckConstraint("status IN ('PROCESSING','CONFIRMED','COMPLETED','CANCELLED')", name="ck_booking_status"),
        CheckConstraint("payment_status IN ('PENDING','PAID','FAILED')", name="ck_payment_status"),
        CheckConstraint("final_price_usd >= 0", name="ck_final_price_usd_non_negative"),
        CheckConstraint("final_price_mmk >= 0", name="ck_final_price_mmk_non_negative"),
        Index("idx_booking_status", "status"),
        Index("idx_booking_payment_status", "payment_status"),
        Index("idx_booking_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    booking_number: Mapped[int] = mapped_column(
        Integer,
        booking_number_seq,
        server_default=booking_number_seq.next_value(),
        nullable=False,
        unique=True,
    )
    booking_code: Mapped[str | None] = mapped_column(String, nullable=True, unique=True)
    customer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("customer_users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String, nullable=False)
    bundle_key: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    adults: Mapped[int] = mapped_column(Integer, nullable=False)
    flight_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    final_price_usd: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    final_price_mmk: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    outbound_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    inbound_completed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    status: Mapped[str] = mapped_column(String, default="PROCESSING", nullable=False)
    status_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status_updated_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)

    payment_status: Mapped[str] = mapped_column(String, default="PENDING", nullable=False)
    payment_marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payment_marked_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)

    ticket_file_url: Mapped[str | None] = mapped_column(String, nullable=True)
    ticket_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ticket_uploaded_by_admin_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    passengers = relationship("BookingPassenger", back_populates="booking", cascade="all, delete-orphan")
