import json
from urllib.parse import quote

from pydantic import field_validator, model_validator
from sqlalchemy.engine import URL
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Air Ticket Booking API"
    APP_DESCRIPTION: str = "Backend API for flight search and booking system"
    APP_VERSION: str = "1.0.0"
    APP_ROOT_MESSAGE: str = "FastAPI running in Docker"
    ENVIRONMENT: str = "development"
    BASE_URL: str = "http://localhost:8000"

    # Database
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "db"
    POSTGRES_PORT: int = 5432

    # Auth / JWT
    JWT_SECRET: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    TOKEN_EXPIRE_MINUTES_RESET: int = 30
    TOKEN_EXPIRE_MINUTES_VERIFY: int = 1440

    # Email
    EMAIL_ENABLED: bool = True
    EMAIL_HOST: str = "smtp.example.com"
    EMAIL_PORT: int = 587
    EMAIL_USERNAME: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_FROM: str = ""
    EMAIL_FROM_NAME: str = ""
    EMAIL_USE_TLS: bool = True
    EMAIL_USE_SSL: bool = False
    EMAIL_REQUIRE_AUTH: bool = True
    EMAIL_TIMEOUT_SECONDS: int = 30
    FRONTEND_BASE_URL: str = "http://localhost:3000"

    # Auth rate limiting
    RATE_LIMIT_FORGOT_PASSWORD: int = 5
    RATE_LIMIT_RESEND_EMAIL: int = 5
    RATE_LIMIT_WINDOW_SECONDS: int = 3600

    # CORS
    CORS_ALLOW_ORIGINS: list[str] | str = []

    # External Flight API
    TICKET_API_KEY: str

    # Redis
    REDIS_PASSWORD: str = ""
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    FLIGHT_CACHE_TTL: int = 900
    TRUSTED_PROXY_CIDRS: str = "127.0.0.1/32,172.16.0.0/12"
    BOOKING_AUTO_CANCEL_EXPIRE_MINUTES: int = 30
    LIFECYCLE_JOB_INTERVAL_MINUTES: int = 5
    STARTUP_DB_MAX_RETRIES: int = 10
    STARTUP_DB_RETRY_DELAY_SECONDS: int = 2

    # File storage
    STORAGE_TYPE: str = "local"
    UPLOAD_DIR: str = "/app/uploads"
    S3_BUCKET: str = ""
    S3_REGION: str = "ap-southeast-1"
    S3_ACCESS_KEY: str = ""
    S3_SECRET_KEY: str = ""
    S3_BASE_URL: str = ""

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
    def _validate_environment(self) -> "Settings":
        if self.ENVIRONMENT.lower() in {"production", "prod"} and "*" in self.cors_origins:
            raise ValueError("CORS wildcard '*' is not allowed when ENVIRONMENT=production")

        return self

    @property
    def cors_origins(self) -> list[str]:
        return self._clean_origins(self.CORS_ALLOW_ORIGINS)

    @property
    def DATABASE_URL(self) -> str:
        return URL.create(
            drivername="postgresql+psycopg2",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        ).render_as_string(hide_password=False)

    @property
    def REDIS_URL(self) -> str:
        auth = ""
        if self.REDIS_PASSWORD:
            auth = f":{quote(self.REDIS_PASSWORD, safe='')}@"
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

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
