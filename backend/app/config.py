import os
from pathlib import Path
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings

_BACKEND_DIR = Path(__file__).resolve().parents[1]

_PLACEHOLDER_PREFIXES = ("your-", "sk-your-", "change-me", "put-your", "insert-")

_API_KEY_FIELDS = ("OPENAI_API_KEY", "GOOGLE_PLACES_API_KEY", "OUTSCRAPER_API_KEY")


def _running_on_railway() -> bool:
    """Railway injects these; used to catch misconfigured DATABASE_URL."""
    return bool(os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"))


def _database_url_looks_localhost(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
        return host in ("localhost", "127.0.0.1", "::1")
    except Exception:
        return False


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/review_insight"
    OPENAI_API_KEY: str = ""
    GOOGLE_PLACES_API_KEY: str = ""

    REVIEW_PROVIDER: str = "mock"
    OUTSCRAPER_API_KEY: str = ""
    OUTSCRAPER_REVIEWS_LIMIT: int = 100
    OUTSCRAPER_SORT: str = "newest"
    OUTSCRAPER_CUTOFF: str = ""
    # Deprecated fields — kept so old .env files don't cause load errors; values are ignored.
    OUTSCRAPER_SKIP: int = 0
    USE_MOCK_REVIEWS: bool = True

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Comma-separated extra CORS origins (e.g. https://my-app.up.railway.app). Localhost is always allowed.
    CORS_ORIGINS: str = ""

    # Debug tracing — set to "true" to enable E2E request tracing ring buffer.
    DEBUG_TRACE: bool = False

    model_config = {"env_file": str(_BACKEND_DIR / ".env"), "extra": "ignore"}

    @model_validator(mode="after")
    def _resolve_provider_and_keys(self) -> "Settings":
        for field in _API_KEY_FIELDS:
            val = getattr(self, field)
            if val and any(val.lower().startswith(p) for p in _PLACEHOLDER_PREFIXES):
                object.__setattr__(self, field, "")

        return self

    @model_validator(mode="after")
    def _reject_localhost_db_on_railway(self) -> "Settings":
        if _running_on_railway() and _database_url_looks_localhost(self.DATABASE_URL):
            msg = (
                "DATABASE_URL points to localhost, but on Railway the database is a separate service. "
                "In Railway → your backend service → Variables, set DATABASE_URL using "
                '"Reference" from the PostgreSQL plugin (or paste its connection string). '
                "Do not use localhost inside the container. See docs/STAGING.md."
            )
            raise ValueError(msg)
        return self


settings = Settings()
