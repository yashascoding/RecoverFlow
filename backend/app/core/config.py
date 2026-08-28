from __future__ import annotations

from enum import Enum
from functools import lru_cache
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "RecoverFlow"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Environment = Environment.DEVELOPMENT
    DEBUG: bool = True
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # Postgres
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "recoverflow"
    POSTGRES_PASSWORD: str = "recoverflow123"
    POSTGRES_DB: str = "recoverflow"
    DATABASE_URL: str | None = None

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str | None = None

    # Razorpay
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # Resend (email)
    RESEND_API_KEY: str = ""
    RESEND_WEBHOOK_SECRET: str = ""
    RECOVERY_EMAIL_FROM: str = ""
    TEST_EMAIL: str = ""

    # Recovery policy
    RECOVERY_LINK_TTL_MINUTES: int = 1440
    MAX_RECOVERY_ATTEMPTS: int = 3
    RECOVERY_RETRY_DELAY_MINUTES: int = 30
    CONTACT_QUIET_HOURS_START: str = "21:00"
    CONTACT_QUIET_HOURS_END: str = "09:00"
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Logging
    LOG_LEVEL: str = "INFO"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: str | None, info) -> str:
        if v:
            return v
        data = info.data
        return (
            f"postgresql+asyncpg://{data.get('POSTGRES_USER', 'recoverflow')}"
            f":{data.get('POSTGRES_PASSWORD', 'recoverflow123')}"
            f"@{data.get('POSTGRES_HOST', 'localhost')}:{data.get('POSTGRES_PORT', 5432)}"
            f"/{data.get('POSTGRES_DB', 'recoverflow')}"
        )

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def build_redis_url(cls, v: str | None, info) -> str:
        if v:
            return v
        data = info.data
        return f"redis://{data.get('REDIS_HOST', 'localhost')}:{data.get('REDIS_PORT', 6379)}"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == Environment.PRODUCTION


@lru_cache
def get_settings() -> Settings:
    return Settings()
