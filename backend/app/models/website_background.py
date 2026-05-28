from sqlalchemy import CheckConstraint, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from backend.app.db.base import Base


class WebsiteBackground(Base):
    __tablename__ = "website_background"

    id = Column(Integer, primary_key=True, default=1)
    image_url = Column(String, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_website_background_singleton_id"),
    )
