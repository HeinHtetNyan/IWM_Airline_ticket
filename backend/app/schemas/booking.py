from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class BookingOut(BaseModel):
    booking_id: UUID
    customer_id: UUID
    status: str

    # include if your Booking model has them
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
