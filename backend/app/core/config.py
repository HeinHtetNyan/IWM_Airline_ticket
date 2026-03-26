import json

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Air Ticket Booking API"
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str

    # Auth / JWT
    JWT_SECRET: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ALLOW_ORIGINS: list[str] | str = []

    # External Flight API
    TICKET_API_KEY: str

    # Redis
    REDIS_PASSWORD: str = ""
    REDIS_URL: str
    FLIGHT_CACHE_TTL: int = 900
    TRUSTED_PROXY_CIDRS: str = "127.0.0.1/32,172.16.0.0/12"

    @field_validator("CORS_ALLOW_ORIGINS", mode="before")
    @classmethod
    def _parse_cors_allow_origins(cls, value: list[str] | str | None) -> list[str]:
        if value is None:
            return []

        if isinstance(value, list):
            return cls._clean_origins(value)

        if isinstance(value, str):
            raw_value = value.strip()
            if not raw_value:
                return []

            if raw_value.startswith("[") and raw_value.endswith("]"):
                try:
                    parsed = json.loads(raw_value)
                except json.JSONDecodeError:
                    parsed = raw_value[1:-1].split(",")
                if isinstance(parsed, list):
                    return cls._clean_origins(parsed)

            return cls._clean_origins(raw_value.split(","))

        raise TypeError("CORS_ALLOW_ORIGINS must be a list or comma-separated string")

    @staticmethod
    def _clean_origins(origins: list[str] | list[object]) -> list[str]:
        cleaned: list[str] = []
        for origin in origins:
            normalized = str(origin).strip().strip("\"'")
            if normalized:
                cleaned.append(normalized)
        return cleaned

    @model_validator(mode="after")
    def _expand_redis_url(self) -> "Settings":
        if self.REDIS_PASSWORD:
            self.REDIS_URL = self.REDIS_URL.replace("${REDIS_PASSWORD}", self.REDIS_PASSWORD)

        if self.ENVIRONMENT.lower() in {"production", "prod"} and "*" in self.cors_origins:
            raise ValueError("CORS wildcard '*' is not allowed when ENVIRONMENT=production")

        return self

    @property
    def cors_origins(self) -> list[str]:
        return self._clean_origins(self.CORS_ALLOW_ORIGINS)

    # DB Pool
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 40
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800

    # Booking retention
    CANCELLED_BOOKING_DELETE_DAYS: int = 7

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
