from pydantic import BaseModel
from datetime import date


class FlightOverrideBase(BaseModel):
    airline_code: str
    flight_number: str
    departure_date: date
    override_price_usd: float


class FlightOverrideCreate(FlightOverrideBase):
    pass


class FlightOverrideUpdate(BaseModel):
    override_price_usd: float


class FlightOverrideResponse(FlightOverrideBase):
    id: str

    class Config:
        from_attributes = True
