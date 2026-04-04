from datetime import datetime

from pydantic import BaseModel, Field


class PricingConfigUpdate(BaseModel):
    global_markup_percentage: float = Field(..., ge=0)


class PricingConfigResponse(BaseModel):
    id: int
    global_markup_percentage: float
    updated_at: datetime | None

    class Config:
        from_attributes = True
