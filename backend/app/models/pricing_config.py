from sqlalchemy import CheckConstraint, Column, DateTime, Float, Integer
from sqlalchemy.sql import func

from backend.app.db.base import Base


class PricingConfig(Base):
    __tablename__ = "pricing_config"

    id = Column(Integer, primary_key=True, default=1)
    global_markup_percentage = Column(Float, nullable=False, default=15.0)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_pricing_config_singleton_id"),
        CheckConstraint("global_markup_percentage >= 0", name="ck_pricing_config_markup_non_negative"),
    )
