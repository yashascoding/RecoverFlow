from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "recoverflow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "recoverflow"
    POSTGRES_PASSWORD: str = "recoverflow123"
    POSTGRES_DB: str = "recoverflow_db"

    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    DATABASE_URL: str | None = None
    REDIS_URL: str | None = None

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, value):
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

settings = Settings()
