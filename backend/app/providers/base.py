from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TypedDict


class NormalizedReview(TypedDict):
    external_id: str
    source: str
    author: str | None
    rating: int
    text: str | None
    published_at: datetime | None


class ReviewProvider(ABC):
    """Interface that every review-fetching provider must implement."""

    @abstractmethod
    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        """Fetch reviews for a place and return them in normalized form.

        Args:
            place_id: The stored place identifier (may be a hex CID).
            google_maps_url: The original Google Maps URL, if available.
                Providers that support URL-based lookup can use this
                for more reliable results.

        Implementations should handle their own API authentication, error
        handling, and response parsing.  The returned dicts must conform
        to the NormalizedReview shape so review_service can persist them
        without knowing which provider was used.
        """
