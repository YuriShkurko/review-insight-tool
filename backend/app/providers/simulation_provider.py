from __future__ import annotations

import logging

from sqlalchemy import text

from app.database import SessionLocal
from app.providers.base import NormalizedReview, ReviewProvider

logger = logging.getLogger(__name__)


class SimulationProvider(ReviewProvider):
    """Returns reviews from the sim_reviews table for the living demo world.

    The table is populated by scripts/seed_demo.py (initial seed) and
    scripts/tick_demo.py (ongoing wave ticks). The provider is read-only —
    it never writes.
    """

    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        with SessionLocal() as db:
            rows = db.execute(
                text(
                    """
                    SELECT external_id, author, rating, text, published_at
                    FROM sim_reviews
                    WHERE place_id = :place_id
                    ORDER BY published_at DESC
                    """
                ),
                {"place_id": place_id},
            ).fetchall()

        if not rows:
            logger.warning("op=sim_fetch place_id=%s no rows found", place_id)
            return []

        result: list[NormalizedReview] = [
            NormalizedReview(
                external_id=row.external_id,
                source="simulation",
                author=row.author,
                rating=row.rating,
                text=row.text,
                published_at=row.published_at,
            )
            for row in rows
        ]

        logger.info("op=sim_fetch place_id=%s reviews=%d", place_id, len(result))
        return result
