from pydantic import model_validator
from pydantic_settings import BaseSettings

_PLACEHOLDER_PREFIXES = ("your-", "sk-your-", "change-me", "put-your", "insert-")

_API_KEY_FIELDS = ("OPENAI_API_KEY", "GOOGLE_PLACES_API_KEY", "OUTSCRAPER_API_KEY")


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

    model_config = {"env_file": ".env", "extra": "ignore"}

    @model_validator(mode="after")
    def _resolve_provider_and_keys(self) -> "Settings":
        for field in _API_KEY_FIELDS:
            val = getattr(self, field)
            if val and any(val.lower().startswith(p) for p in _PLACEHOLDER_PREFIXES):
                object.__setattr__(self, field, "")

        return self


settings = Settings()
