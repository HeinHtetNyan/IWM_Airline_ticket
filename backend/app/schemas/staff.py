from uuid import UUID
from pydantic import BaseModel, EmailStr


class StaffBase(BaseModel):
    name: str
    email: EmailStr


class StaffCreate(StaffBase):
    password: str


class StaffUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None


class StaffResponse(StaffBase):
    id: UUID
    role: str
    is_active: bool

    class Config:
        from_attributes = True