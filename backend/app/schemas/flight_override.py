from datetime import date

from pydantic import BaseModel, Field


class FlightOverrideBase(BaseModel):
    airline_code: str
    flight_number: str
    departure_date: date
    override_price_usd: float = Field(..., gt=0)


class FlightOverrideCreate(FlightOverrideBase):
    pass


class FlightOverrideUpdate(BaseModel):
    override_price_usd: float = Field(..., gt=0)


class FlightOverrideResponse(FlightOverrideBase):
    id: str

    class Config:
        from_attributes = True
