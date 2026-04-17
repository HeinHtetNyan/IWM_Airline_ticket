from pydantic import BaseModel, Field


class Message(BaseModel):
    message: str


class ExchangeRateUpdate(BaseModel):
    usd_to_mmk: float = Field(
        ..., gt=0, le=100000, description="USD to MMK exchange rate"
    )
