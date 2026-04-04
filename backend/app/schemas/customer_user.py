from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class CustomerUserUpdate(BaseModel):
    full_name: str | None = None
    phone: str | None = None


class CustomerUserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None
    phone: str | None
    is_email_verified: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
