from typing import Any, Dict

from pydantic import BaseModel, EmailStr, Field, field_validator


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


class _EmailPasswordBase(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: EmailStr) -> str:
        return str(v).strip().lower()


class CustomerSignupIn(_EmailPasswordBase):
    full_name: str = Field(..., min_length=1, max_length=120)
    phone: str = Field(..., min_length=5, max_length=32)


class LoginIn(_EmailPasswordBase):
    pass


# Admin
class AdminSignupRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "STAFF"


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class AdminOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    is_active: bool
