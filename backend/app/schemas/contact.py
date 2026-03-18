from datetime import datetime
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactBase(BaseModel):
    given_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    country_of_residence: str = Field(..., min_length=1, max_length=100)
    phone_number: str = Field(..., min_length=1, max_length=30)

    @field_validator("given_name", "last_name", "country_of_residence", "phone_number")
    @classmethod
    def validate_non_empty_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("must not be empty")
        return value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: EmailStr) -> str:
        return str(value).strip().lower()


class ContactCreate(ContactBase):
    pass


class ContactUpdate(ContactBase):
    pass


class ContactOut(ContactBase):
    id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
