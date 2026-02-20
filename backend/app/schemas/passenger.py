from datetime import date, datetime
from typing import List
from uuid import UUID
from pydantic import BaseModel, Field


# Single Passenger Create
class PassengerCreate(BaseModel):
    given_name: str
    last_name: str

    passport_number: str

    gender: str  # "MALE" or "FEMALE"

    date_of_birth: date

    nationality: str

    phone_number: str


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
    phone_number: str

    created_at: datetime

    class Config:
        from_attributes = True
