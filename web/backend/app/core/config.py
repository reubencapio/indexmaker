"""
Application configuration using Pydantic Settings.

Environment variables are loaded from .env file or system environment.
"""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "IndexMaker"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # API
    API_V1_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Security
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "indexmaker"
    POSTGRES_PASSWORD: str = "indexmaker"
    POSTGRES_DB: str = "indexmaker"
    DATABASE_URL: PostgresDsn | None = None

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: str | None, info: Any) -> str:
        if v:
            return v
        values = info.data
        return str(
            PostgresDsn.build(
                scheme="postgresql+asyncpg",
                username=values.get("POSTGRES_USER"),
                password=values.get("POSTGRES_PASSWORD"),
                host=values.get("POSTGRES_HOST"),
                port=values.get("POSTGRES_PORT"),
                path=values.get("POSTGRES_DB"),
            )
        )

    # Redis (for Celery)
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_URL: str = "redis://localhost:6379/0"

    # Celery
    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v: str | None, info: Any) -> str:
        if isinstance(v, str) and v:
            return v
        return info.data.get("REDIS_URL", "redis://localhost:6379/0")

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v: str | None, info: Any) -> str:
        if isinstance(v, str) and v:
            return v
        return info.data.get("REDIS_URL", "redis://localhost:6379/0")

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Index calculation
    MAX_INDEX_COMPONENTS: int = 500
    DEFAULT_BACKTEST_YEARS: int = 5

    # AI / LLM Configuration
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
