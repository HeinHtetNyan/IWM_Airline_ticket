from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr


class ContactCreate(BaseModel):
    given_name: str
    last_name: str
    email: EmailStr
    country_of_residence: str
    phone_number: str


class ContactOut(BaseModel):
    id: UUID
    given_name: str
    last_name: str
    email: EmailStr
    country_of_residence: str
    phone_number: str
    created_at: datetime

    class Config:
        from_attributes = True
