from typing import Any, Dict

from pydantic import BaseModel, EmailStr, field_validator


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class _AuthBase(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class CustomerSignupIn(_AuthBase):
    full_name: str
    phone: str


class LoginIn(_AuthBase):
    pass


class AdminSignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str = "STAFF"


class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class AdminOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
