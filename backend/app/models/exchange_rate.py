from sqlalchemy import Column, Float, DateTime
from sqlalchemy.sql import func
from backend.app.db.base import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Float, primary_key=True, default=1)
    usd_to_mmk = Column(Float, nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
