from pydantic import BaseModel, EmailStr
from typing import Optional, Dict, Any
from pydantic import field_validator


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class CustomerSignupIn(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password too long (max 72 bytes)")
        return v

class LoginIn(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v:
            raise ValueError("Invalid email")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password too long (max 72 bytes)")
        return v

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
