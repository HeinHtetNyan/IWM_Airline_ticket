from sqlalchemy import Column, String, Boolean, DateTime, Float
from sqlalchemy.sql import func

from app.db.base import Base


class Flight(Base):
    __tablename__ = "flights"

    # Internal ID
    id = Column(String, primary_key=True, index=True)

    # External API identity
    external_flight_id = Column(String, unique=True, index=True, nullable=False)

    airline_code = Column(String, index=True, nullable=False)
    flight_number = Column(String, index=True, nullable=False)

    origin = Column(String, index=True, nullable=False)
    destination = Column(String, index=True, nullable=False)

    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)

    # Admin control
    is_published = Column(Boolean, default=False)
    is_visible = Column(Boolean, default=True)

    # Availability tracking
    is_available = Column(Boolean, default=True)
    last_seen_at = Column(DateTime, nullable=False)

    # Pricing
    base_price_usd = Column(Float, nullable=True)
    override_price_usd = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
