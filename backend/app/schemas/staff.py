from uuid import UUID
from pydantic import BaseModel, EmailStr, field_validator

MAX_BCRYPT_BYTES = 72


class StaffBase(BaseModel):
    name: str
    email: EmailStr


class StaffCreate(StaffBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode("utf-8")) > MAX_BCRYPT_BYTES:
            raise ValueError(f"Password cannot exceed {MAX_BCRYPT_BYTES} bytes")
        return v


class StaffUpdate(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None
    is_active: bool | None = None

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str | None) -> str | None:
        if v is None:
            return v
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v.encode("utf-8")) > MAX_BCRYPT_BYTES:
            raise ValueError(f"Password cannot exceed {MAX_BCRYPT_BYTES} bytes")
        return v


class StaffResponse(StaffBase):
    id: UUID
    role: str
    is_active: bool

    class Config:
        from_attributes = True
