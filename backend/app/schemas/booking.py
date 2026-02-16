from datetime import datetime, date
from typing import Optional
from uuid import UUID
from pydantic import BaseModel


# Request Schema (Create)
class BookingCreate(BaseModel):
    airline_code: str
    flight_number: str
    origin: str
    destination: str
    departure_time: str
    arrival_time: str
    final_price_usd: float
    final_price_mmk: float


# Response Schema
class BookingOut(BaseModel):
    booking_id: UUID
    airline_code: str
    flight_number: str
    origin: str
    destination: str
    departure_date: date
    departure_time: str
    arrival_time: str
    final_price_usd: float
    final_price_mmk: float
    status: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# Admin Status Update
class BookingStatusUpdate(BaseModel):
    status: str
