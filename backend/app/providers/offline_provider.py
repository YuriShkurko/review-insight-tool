from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.providers.base import NormalizedReview, ReviewProvider

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "offline"


class OfflineProvider(ReviewProvider):
    """Loads reviews from local JSON files for demos, testing, and CI.

    Each business is identified by place_id. The provider looks for a
    matching entry in manifest.json, then reads the associated reviews file.
    """

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _DATA_DIR
        self._manifest = self._load_manifest()

    def _load_manifest(self) -> dict[str, dict]:
        manifest_path = self._data_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning("op=offline_provider manifest not found at %s", manifest_path)
            return {}
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        return {b["place_id"]: b for b in data.get("businesses", [])}

    def fetch_reviews(
        self, place_id: str, google_maps_url: str | None = None
    ) -> list[NormalizedReview]:
        entry = self._manifest.get(place_id)
        if not entry:
            logger.warning("op=offline_fetch place_id=%s not found in manifest", place_id)
            return []

        reviews_file = self._data_dir / entry["reviews_file"]
        if not reviews_file.exists():
            logger.warning("op=offline_fetch file=%s not found", reviews_file)
            return []

        with open(reviews_file, encoding="utf-8") as f:
            raw_reviews: list[dict] = json.load(f)

        result: list[NormalizedReview] = []
        fallback_date = datetime(2026, 3, 1, tzinfo=timezone.utc)
        for i, raw in enumerate(raw_reviews):
            ext_id = hashlib.sha256(f"{place_id}:{i}".encode()).hexdigest()[:16]

            pub_at: datetime | None = None
            if raw.get("published_at"):
                try:
                    pub_at = datetime.fromisoformat(raw["published_at"])
                except (ValueError, TypeError):
                    pass
            if pub_at is None:
                pub_at = fallback_date - timedelta(days=i * 3, hours=i * 5)

            result.append(NormalizedReview(
                external_id=f"offline_{ext_id}",
                source="offline",
                author=raw.get("author"),
                rating=raw["rating"],
                text=raw.get("text"),
                published_at=pub_at,
            ))

        logger.info(
            "op=offline_fetch place_id=%s reviews=%d file=%s",
            place_id, len(result), entry["reviews_file"],
        )
        return result
