import uuid

from sqlalchemy import Boolean, CheckConstraint, Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func, text

from backend.app.db.base import Base


class WebsiteBanner(Base):
    __tablename__ = "website_banners"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String, nullable=False)
    image_url = Column(String, nullable=False)
    destination_code = Column(String, nullable=False)
    priority = Column(Integer, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    created_at = Column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    __table_args__ = (
        CheckConstraint(
            "priority >= 1 AND priority <= 8",
            name="ck_banner_priority_range",
        ),
        # Partial unique index: priority must be unique among active banners only.
        # Inactive (soft-deleted) banners can reuse the same priority slot.
        Index(
            "ix_banner_active_priority_unique",
            "priority",
            unique=True,
            postgresql_where=text("is_active = true"),
        ),
    )
