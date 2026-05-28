from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class CustomerMeResponse(BaseModel):
    id: UUID
    email: str
    full_name: str | None
    phone: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CustomerUpdateRequest(BaseModel):
    full_name: str | None = None
    phone: str | None = None

    @field_validator("full_name", "phone", mode="before")
    @classmethod
    def normalize_optional_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = str(value).strip()
        return normalized or None
