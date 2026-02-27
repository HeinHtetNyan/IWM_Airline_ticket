from sqlalchemy import Column, String
from backend.app.db.base import Base


class Airport(Base):
    __tablename__ = "airports"

    code = Column(String, primary_key=True, index=True)  # Airport code
    timezone = Column(String, nullable=False)  # timezone string
