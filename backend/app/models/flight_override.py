import uuid
from sqlalchemy import CheckConstraint, Column, Date, DateTime, Float, String, UniqueConstraint
from sqlalchemy.sql import func

from app.db.base import Base


class FlightOverride(Base):
    __tablename__ = "flight_overrides"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    airline_code = Column(String, index=True, nullable=False)
    flight_number = Column(String, index=True, nullable=False)
    departure_date = Column(Date, index=True, nullable=False)
    override_price_usd = Column(Float, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("airline_code", "flight_number", "departure_date", name="uq_override_flight_date"),
        CheckConstraint("override_price_usd > 0", name="ck_override_price_positive"),
    )
