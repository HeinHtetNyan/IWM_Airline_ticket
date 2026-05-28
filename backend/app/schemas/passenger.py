from datetime import date, datetime
from enum import Enum
from typing import Annotated, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class Gender(str, Enum):
    MALE = "MALE"
    FEMALE = "FEMALE"


class PassengerCreate(BaseModel):
    given_name: str
    last_name: str
    passport_number: str = Field(..., min_length=4, max_length=20)
    gender: Gender
    date_of_birth: date
    nationality: str = Field(..., min_length=2, max_length=56)
    phone_number: str

    @field_validator("date_of_birth")
    @classmethod
    def validate_dob(cls, value: date) -> date:
        if value > date.today() or value.year < 1900:
            raise ValueError("date_of_birth is out of range")
        return value


class PassengerBulkCreate(BaseModel):
    passengers: Annotated[List[PassengerCreate], Field(min_length=1, max_length=9)]


class PassengerOut(BaseModel):
    id: UUID
    booking_id: UUID
    given_name: str
    last_name: str
    passport_number: str
    gender: str
    date_of_birth: date
    nationality: str
    phone_number: str
    created_at: datetime

    class Config:
        from_attributes = True
