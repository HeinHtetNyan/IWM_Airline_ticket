import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, Date, DateTime, Float, Index, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from backend.app.db.base import Base


class PriceOverride(Base):
    __tablename__ = "price_overrides"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    airline_code = Column(String, nullable=False, index=True)
    flight_number = Column(String, nullable=False, index=True)
    departure_date = Column(Date, nullable=False, index=True)
    override_price_usd = Column(Float, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        CheckConstraint("override_price_usd > 0", name="ck_price_override_price_positive"),
        Index(
            "ix_price_overrides_flight_active",
            "airline_code",
            "flight_number",
            "departure_date",
            "is_active",
        ),
    )
