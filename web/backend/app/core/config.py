"""
Application configuration using Pydantic Settings.

Environment variables are loaded from .env file or system environment.
"""

from functools import lru_cache
from typing import Any

from pydantic import PostgresDsn, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_SECRET_KEY = "your-secret-key-change-in-production"


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        # Load from multiple .env files: backend local .env first, then root .env
        # Later files in the tuple take precedence for duplicate keys
        env_file=(".env", "../../.env"),
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
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "https://indexforge.ai",
        "https://www.indexforge.ai",
        "https://indexforge.vercel.app",
        "https://api.indexforge.ai",
        # Legacy domains
        "https://indexmaker.ai",
        "https://www.indexmaker.ai",
        "https://indexmaker.vercel.app",
        "https://api.indexmaker.ai",
    ]

    # Security
    SECRET_KEY: str = DEFAULT_SECRET_KEY
    # Key for encrypting stored third-party credentials (SFTP passwords and
    # keys). Falls back to SECRET_KEY. Changing whichever is in use makes existing
    # stored credentials unreadable; users then have to re-enter them.
    CREDENTIAL_ENCRYPTION_KEY: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    ALGORITHM: str = "HS256"

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "indexforge"
    POSTGRES_PASSWORD: str = "indexforge"
    POSTGRES_DB: str = "indexforge"
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

    # Celery - use REDIS_URL directly, with fallback to localhost
    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    @field_validator("CELERY_BROKER_URL", mode="before")
    @classmethod
    def assemble_celery_broker(cls, v: str | None, info: Any) -> str:
        # If explicitly set and not empty, use it
        if v and isinstance(v, str) and v.strip():
            return v.strip()
        # Try to get REDIS_URL from environment directly
        import os

        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url and redis_url.strip():
            return redis_url.strip()
        # Fall back to info.data if available
        redis_from_data = info.data.get("REDIS_URL", "") if info.data else ""
        if redis_from_data and redis_from_data.strip():
            return redis_from_data.strip()
        # Ultimate fallback
        return "redis://localhost:6379/0"

    @field_validator("CELERY_RESULT_BACKEND", mode="before")
    @classmethod
    def assemble_celery_backend(cls, v: str | None, info: Any) -> str:
        # If explicitly set and not empty, use it
        if v and isinstance(v, str) and v.strip():
            return v.strip()
        # Try to get REDIS_URL from environment directly
        import os

        redis_url = os.environ.get("REDIS_URL", "")
        if redis_url and redis_url.strip():
            return redis_url.strip()
        # Fall back to info.data if available
        redis_from_data = info.data.get("REDIS_URL", "") if info.data else ""
        if redis_from_data and redis_from_data.strip():
            return redis_from_data.strip()
        # Ultimate fallback
        return "redis://localhost:6379/0"

    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    # Endpoints that call a paid LLM per request get their own, much smaller budget.
    AI_RATE_LIMIT_PER_HOUR: int = 20

    # Index calculation
    MAX_INDEX_COMPONENTS: int = 500
    DEFAULT_BACKTEST_YEARS: int = 5
    # Round-trip cost charged against backtest turnover at each rebalance. A
    # zero-cost backtest overstates any strategy that trades, and the effect
    # compounds with rebalancing frequency.
    TRANSACTION_COST_BPS: float = 10.0

    # AI / LLM Configuration
    GEMINI_API_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    # Model ids are settings, not constants: preview models get retired on the
    # provider's schedule, and swapping an env var beats shipping a code change
    # every time that happens.
    # Claude is tried first when ANTHROPIC_API_KEY is set; Gemini and OpenAI are
    # fallbacks if their keys are present.
    ANTHROPIC_API_KEY: str | None = None
    ANTHROPIC_MODEL: str = "claude-opus-5-5"
    # A Flash model, because Google's free tier gives the Pro previews almost no
    # quota and every request then fails with a 429.
    GEMINI_MODEL: str = "gemini-3.5-flash"
    OPENAI_MODEL: str = "gpt-4o"

    # Email / SMTP Configuration (Privateemail.com)
    SMTP_HOST: str = "mail.privateemail.com"
    SMTP_PORT: int = 465
    SMTP_USER: str | None = None  # e.g., support@indexmaker.ai
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "support@indexmaker.ai"
    SMTP_FROM_NAME: str = "IndexMaker Support"
    SUPPORT_EMAIL: str = "support@indexmaker.ai"  # Where to send contact form emails

    # Celery toggle for local development
    # When False, tasks run synchronously (no Redis/Celery needed)
    # When True, tasks are queued to Celery (requires Redis + worker)
    CELERY_ENABLED: bool = False

    # Frontend URL: where Stripe Checkout, the billing portal and password-reset
    # emails send people back to. Set it explicitly in every deployment.
    FRONTEND_URL: str = ""

    @field_validator("FRONTEND_URL", mode="after")
    @classmethod
    def default_frontend_url(cls, v: str, info: Any) -> str:
        if v:
            return v.rstrip("/")
        # Unset. Outside local development, falling back to localhost would send
        # a paying customer to a dead page straight after checkout.
        return "http://localhost:3000" if info.data.get("DEBUG") else "https://www.indexmaker.ai"

    # Payment / Stripe
    STRIPE_SECRET_KEY: str | None = None
    STRIPE_PUBLISHABLE_KEY: str | None = None
    STRIPE_WEBHOOK_SECRET: str | None = None
    # Pro is sold monthly and annually. Each id is a recurring Stripe Price; the
    # amount shown on the pricing page is read from Stripe, never hard-coded.
    STRIPE_PRO_MONTHLY_PRICE_ID: str | None = None
    STRIPE_PRO_ANNUAL_PRICE_ID: str | None = None
    # Legacy single price, still honoured if the two above are unset.
    STRIPE_PRO_PRICE_ID: str | None = None
    # Free-trial length for a customer's first subscription. 0 disables trials.
    STRIPE_TRIAL_DAYS: int = 0

    @model_validator(mode="after")
    def reject_default_secret_in_production(self) -> "Settings":
        # The default key is public (it is in this file). Signing tokens with it
        # in production would let anyone mint a valid login for any account.
        if self.ENVIRONMENT.lower() == "production" and (
            not self.SECRET_KEY.strip() or self.SECRET_KEY == DEFAULT_SECRET_KEY
        ):
            raise ValueError("SECRET_KEY must be set to a private value in production")
        return self


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
