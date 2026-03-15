from sqlalchemy import Column, Integer, Numeric, DateTime
from sqlalchemy.sql import func
from backend.app.db.base import Base


class ExchangeRate(Base):
    __tablename__ = "exchange_rates"

    id = Column(Integer, primary_key=True)
    usd_to_mmk = Column(Numeric(10, 4), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
