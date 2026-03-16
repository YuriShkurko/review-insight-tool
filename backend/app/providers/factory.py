from app.config import settings
from app.providers.base import ReviewProvider


def get_review_provider() -> ReviewProvider:
    """Return the configured review provider instance.

    Controlled by the REVIEW_PROVIDER environment variable.
    Supported values: mock, offline, outscraper.
    """
    name = settings.REVIEW_PROVIDER

    if name == "mock":
        from app.providers.mock_provider import MockProvider

        return MockProvider()

    if name == "offline":
        from app.providers.offline_provider import OfflineProvider

        return OfflineProvider()

    if name == "outscraper":
        from app.providers.outscraper_provider import OutscraperProvider

        return OutscraperProvider(
            api_key=settings.OUTSCRAPER_API_KEY,
            reviews_limit=settings.OUTSCRAPER_REVIEWS_LIMIT,
            sort=settings.OUTSCRAPER_SORT,
            cutoff=settings.OUTSCRAPER_CUTOFF,
        )

    supported = ("mock", "offline", "outscraper")
    raise ValueError(
        f"Unknown REVIEW_PROVIDER '{name}'. Supported providers: {', '.join(supported)}"
    )
