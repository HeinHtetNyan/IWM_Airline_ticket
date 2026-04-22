from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class BackgroundResponse(BaseModel):
    image_url: str
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class BackgroundUpdate(BaseModel):
    image_url: str


class BannerResponse(BaseModel):
    id: UUID
    title: str
    image_url: str
    destination_code: str
    priority: int
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


class BannerCreate(BaseModel):
    title: str
    image_url: str
    destination_code: str
    priority: int = Field(..., ge=1, le=8)


class BannerUpdate(BaseModel):
    title: Optional[str] = None
    image_url: Optional[str] = None
    destination_code: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=8)
    is_active: Optional[bool] = None
