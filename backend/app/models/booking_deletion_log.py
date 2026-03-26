import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from backend.app.db.base import Base


class BookingDeletionLog(Base):
    __tablename__ = "booking_deletion_logs"

    __table_args__ = (
        CheckConstraint(
            "deleted_role IN ('STAFF','SUPER_ADMIN','SYSTEM')",
            name="ck_booking_deletion_log_role",
        ),
        CheckConstraint(
            "reason IN ('manual_delete','auto_delete')",
            name="ck_booking_deletion_log_reason",
        ),
        Index("idx_booking_deletion_logs_booking_id", "booking_id"),
        Index("idx_booking_deletion_logs_deleted_at", "deleted_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    booking_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    deleted_by: Mapped[str] = mapped_column(String(50), nullable=False)
    deleted_role: Mapped[str] = mapped_column(String(20), nullable=False)
    deleted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(20), nullable=False)
