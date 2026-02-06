from datetime import datetime
from pydantic import BaseModel


class FlightOut(BaseModel):
    id: str
    airline_code: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime

    is_published: bool
    is_visible: bool
    is_available: bool

    base_price_usd: float | None
    override_price_usd: float | None

    last_seen_at: datetime

    class Config:
        from_attributes = True


class AdminFlightUpdate(BaseModel):
    is_published: bool | None = None
    is_visible: bool | None = None
    override_price_usd: float | None = None

class UserFlightOut(BaseModel):
    airline_code: str
    flight_number: str
    origin: str
    destination: str
    departure_time: datetime
    arrival_time: datetime
    base_price_usd: float

    class Config:
        from_attributes = True
