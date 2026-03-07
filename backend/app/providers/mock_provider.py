from app.mock.reviews import generate_mock_reviews
from app.providers.base import NormalizedReview, ReviewProvider


class MockProvider(ReviewProvider):
    """Returns deterministic mock reviews for development and testing."""

    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        return generate_mock_reviews(place_id)
