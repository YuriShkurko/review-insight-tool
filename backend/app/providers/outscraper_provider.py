from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

from fastapi import HTTPException
from outscraper import ApiClient

from app.providers.base import NormalizedReview, ReviewProvider

logger = logging.getLogger(__name__)

class OutscraperProvider(ReviewProvider):
    """Fetches Google Maps reviews via the Outscraper API."""

    def __init__(
        self,
        api_key: str,
        reviews_limit: int = 100,
        sort: str = "newest",
        cutoff: str = "",
    ):
        if not api_key:
            raise ValueError("OUTSCRAPER_API_KEY is required for the outscraper provider.")
        self._client = ApiClient(api_key=api_key)
        self._reviews_limit = reviews_limit
        self._sort = sort
        self._cutoff = cutoff.strip() if cutoff else ""

    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        query = google_maps_url or place_id
        cutoff_ts = int(self._cutoff) if self._cutoff.isdigit() else None
        logger.info(
            "op=outscraper_fetch query=%s reviews_limit=%d sort=%s cutoff=%s",
            query[:80], self._reviews_limit, self._sort,
            cutoff_ts if cutoff_ts is not None else "none",
        )
        kwargs: dict = {
            "reviews_limit": self._reviews_limit,
            "language": "en",
            "sort": self._sort,
        }
        if cutoff_ts is not None:
            kwargs["cutoff"] = cutoff_ts
        try:
            results = self._client.google_maps_reviews(query, **kwargs)
        except Exception as exc:
            logger.error(
                "op=outscraper_fetch success=false error=%s detail=%s",
                type(exc).__name__, exc,
            )
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
