from datetime import date, datetime
from enum import Enum
from typing import List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class GenderEnum(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


# Single Passenger Create
class PassengerCreate(BaseModel):
    given_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)

    passport_number: str = Field(..., min_length=3, max_length=20)

    gender: GenderEnum

    date_of_birth: date

    nationality: str = Field(..., min_length=2, max_length=56)

    phone_number: str | None = None

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, v: date) -> date:
        today = date.today()
        if v >= today:
            raise ValueError("date_of_birth must be in the past")
        if v.year < 1900:
            raise ValueError("date_of_birth year is too old")
        return v


# Bulk Passenger Create
class PassengerBulkCreate(BaseModel):
    passengers: List[PassengerCreate]


# Passenger Response
class PassengerOut(BaseModel):
    id: UUID
    booking_id: UUID

    given_name: str
    last_name: str
    passport_number: str
    gender: str
    date_of_birth: date
    nationality: str
    phone_number: str | None

    created_at: datetime

    class Config:
        from_attributes = True
