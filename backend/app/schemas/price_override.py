from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class PriceOverrideCreate(BaseModel):
    airline_code: str = Field(..., min_length=1, max_length=16)
    flight_number: str = Field(..., min_length=1, max_length=32)
    departure_date: date
    override_price_usd: float = Field(..., gt=0)
    duration_hours: float | None = Field(default=None, gt=0)

    @field_validator("airline_code", "flight_number")
    @classmethod
    def normalize_code_fields(cls, value: str) -> str:
        return value.strip().upper()


class PriceOverrideResponse(BaseModel):
    id: UUID
    airline_code: str
    flight_number: str
    departure_date: date
    override_price_usd: float
    expires_at: datetime | None
    is_active: bool
    created_at: datetime | None

    class Config:
        from_attributes = True
