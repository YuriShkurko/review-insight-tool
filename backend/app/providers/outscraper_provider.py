from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from outscraper import ApiClient

from app.providers.base import NormalizedReview, ReviewProvider

logger = logging.getLogger(__name__)

_DEFAULT_REVIEWS_LIMIT = 30


class OutscraperProvider(ReviewProvider):
    """Fetches Google Maps reviews via the Outscraper API."""

    def __init__(self, api_key: str, reviews_limit: int = _DEFAULT_REVIEWS_LIMIT):
        if not api_key:
            raise ValueError("OUTSCRAPER_API_KEY is required for the outscraper provider.")
        self._client = ApiClient(api_key=api_key)
        self._reviews_limit = reviews_limit

    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        query = google_maps_url or place_id
        try:
            results = self._client.google_maps_reviews(
                query,
                reviews_limit=self._reviews_limit,
                language="en",
            )
        except Exception as exc:
            logger.error("Outscraper API error for %s: %s", query, exc)
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch reviews from Outscraper. Please try again later.",
            ) from exc

        if not results or not isinstance(results, list) or len(results) == 0:
            return []

        place_data = results[0]
        if not isinstance(place_data, dict):
            return []

        raw_reviews: list[dict] = place_data.get("reviews_data") or []
        return [r for raw in raw_reviews if (r := self._normalize(raw, place_id)) is not None]

    @staticmethod
    def _normalize(raw: dict, place_id: str) -> NormalizedReview | None:
        rating = raw.get("review_rating")
        if rating is None:
            return None

        review_id = raw.get("review_id")
        if review_id:
            external_id = f"outscraper_{review_id}"
        else:
            fallback = f"{place_id}:{raw.get('author_title', '')}:{raw.get('review_text', '')}"
            external_id = f"outscraper_{hashlib.sha256(fallback.encode()).hexdigest()[:16]}"

        published_at = None
        ts = raw.get("review_timestamp")
        if ts:
            try:
                published_at = datetime.fromtimestamp(int(ts), tz=timezone.utc)
            except (ValueError, TypeError, OSError):
                pass

        return NormalizedReview(
            external_id=external_id,
            source="outscraper",
            author=raw.get("author_title"),
            rating=int(rating),
            text=raw.get("review_text"),
            published_at=published_at,
        )
