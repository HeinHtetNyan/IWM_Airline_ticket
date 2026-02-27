import uuid
from datetime import date

from sqlalchemy import Column, String, Float, Date, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy import DateTime

from backend.app.db.base import Base


class FlightOverride(Base):
    __tablename__ = "flight_overrides"

    id = Column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    airline_code = Column(String, index=True, nullable=False)
    flight_number = Column(String, index=True, nullable=False)
    departure_date = Column(Date, index=True, nullable=False)

    override_price_usd = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Prevent duplicate override for same flight/date
    __table_args__ = (
        UniqueConstraint(
            "airline_code",
            "flight_number",
            "departure_date",
            name="uq_override_flight_date",
        ),
    )
