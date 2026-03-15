from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone

import httpx
from fastapi import HTTPException

from app.providers.base import NormalizedReview, ReviewProvider

logger = logging.getLogger(__name__)

_API_BASE = "https://api.app.outscraper.com"
_REQUEST_TIMEOUT = 120  # seconds — hard cap so a single fetch can never block longer


class OutscraperProvider(ReviewProvider):
    """Fetches Google Maps reviews via the Outscraper REST API (no SDK)."""

    def __init__(
        self,
        api_key: str,
        reviews_limit: int = 100,
        sort: str = "newest",
        cutoff: str = "",
    ):
        if not api_key:
            raise ValueError("OUTSCRAPER_API_KEY is required for the outscraper provider.")
        self._api_key = api_key
        self._reviews_limit = reviews_limit
        self._sort = sort
        self._cutoff = cutoff.strip() if cutoff else ""

    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        query = google_maps_url or place_id or ""
        if not query:
            return []

        cutoff_ts = int(self._cutoff) if self._cutoff.isdigit() else None
        logger.info(
            "op=outscraper_fetch query_len=%d query_preview=%s reviews_limit=%d sort=%s cutoff=%s",
            len(query), query[:80] if len(query) > 80 else query,
            self._reviews_limit, self._sort,
            cutoff_ts if cutoff_ts is not None else "none",
        )

        params: dict = {
            "query": query,
            "reviewsLimit": self._reviews_limit,
            "limit": 1,
            "sort": self._sort,
            "language": "en",
            "async": False,
        }
        if cutoff_ts is not None:
            params["cutoff"] = cutoff_ts

        try:
            with httpx.Client(timeout=_REQUEST_TIMEOUT) as client:
                resp = client.get(
                    f"{_API_BASE}/maps/reviews-v3",
                    headers={"X-API-KEY": self._api_key},
                    params=params,
                )
                resp.raise_for_status()
                body = resp.json()
        except httpx.TimeoutException as exc:
            logger.error(
                "op=outscraper_fetch success=false error=Timeout detail=%s timeout=%ds",
                exc, _REQUEST_TIMEOUT,
            )
            raise HTTPException(
                status_code=504,
                detail=f"Outscraper request timed out after {_REQUEST_TIMEOUT}s. Try again or reduce review limit.",
            ) from exc
        except httpx.HTTPStatusError as exc:
            logger.error(
                "op=outscraper_fetch success=false error=HTTPStatus detail=%d %s",
                exc.response.status_code, exc.response.text[:200],
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch reviews from Outscraper. Please try again later.",
            ) from exc
        except Exception as exc:
            logger.error(
                "op=outscraper_fetch success=false error=%s detail=%s",
                type(exc).__name__, exc,
            )
            raise HTTPException(
                status_code=502,
                detail="Failed to fetch reviews from Outscraper. Please try again later.",
            ) from exc

        results = body.get("data", [])
        if not results or not isinstance(results, list) or len(results) == 0:
            return []

        place_data = results[0]
        if not isinstance(place_data, dict):
            return []

        raw_reviews: list[dict] = place_data.get("reviews_data") or []
        logger.info(
            "op=outscraper_fetch success=true reviews_returned=%d",
            len(raw_reviews),
        )
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
