from __future__ import annotations

import contextlib
import hashlib
import json
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from app.providers.base import NormalizedReview, ReviewProvider

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "offline"
_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
_MOJIBAKE_HINT_RE = re.compile(r"(?:Ã|Â|Î|ð|�)")


class OfflineProvider(ReviewProvider):
    """Loads reviews from local JSON files for demos, testing, and CI.

    Each business is identified by place_id. The provider looks for a
    matching entry in manifest.json, then reads the associated reviews file.
    """

    def __init__(self, data_dir: Path | None = None):
        self._data_dir = data_dir or _DATA_DIR
        self._manifest = self._load_manifest()
        self.last_raw_response: list[dict] | None = None

    def _load_manifest(self) -> dict[str, dict]:
        manifest_path = self._data_dir / "manifest.json"
        if not manifest_path.exists():
            logger.warning("op=offline_provider manifest not found at %s", manifest_path)
            return {}
        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)
        return {b["place_id"]: b for b in data.get("businesses", [])}

    @staticmethod
    def _hebrew_score(text: str) -> int:
        return len(_HEBREW_RE.findall(text))

    @staticmethod
    def _repair_mojibake(text: str | None) -> str | None:
        """Best-effort mojibake repair for offline demo text.

        We only replace when a candidate decode increases Hebrew character count.
        This keeps valid English/ASCII text unchanged.
        """
        if not text or not _MOJIBAKE_HINT_RE.search(text):
            return text

        candidates = [text]
        for src_enc, dst_enc in (
            ("latin-1", "utf-8"),
            ("cp1252", "utf-8"),
            ("cp1255", "utf-8"),
        ):
            with contextlib.suppress(UnicodeEncodeError, UnicodeDecodeError):
                candidates.append(text.encode(src_enc).decode(dst_enc))

        best = max(candidates, key=OfflineProvider._hebrew_score)
        return best

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
        self.last_raw_response = raw_reviews

        result: list[NormalizedReview] = []
        fallback_date = datetime(2026, 3, 1, tzinfo=UTC)
        for i, raw in enumerate(raw_reviews):
            ext_id = hashlib.sha256(f"{place_id}:{i}".encode()).hexdigest()[:16]

            pub_at: datetime | None = None
            if raw.get("published_at"):
                with contextlib.suppress(ValueError, TypeError):
                    pub_at = datetime.fromisoformat(raw["published_at"])
            if pub_at is None:
                pub_at = fallback_date - timedelta(days=i * 3, hours=i * 5)

            result.append(
                NormalizedReview(
                    external_id=f"offline_{ext_id}",
                    source="offline",
                    author=self._repair_mojibake(raw.get("author")),
                    rating=raw["rating"],
                    text=self._repair_mojibake(raw.get("text")),
                    published_at=pub_at,
                )
            )

        # Shift all dates so the most recent review lands on today.
        # Keeps relative spacing intact so weekly/monthly tools see real data.
        dated = [r for r in result if r["published_at"] is not None]
        if dated:
            max_pub = max(r["published_at"] for r in dated)  # type: ignore[type-var]
            now = datetime.now(UTC)
            if max_pub < now:
                shift = now - max_pub
                result = [
                    {**r, "published_at": r["published_at"] + shift}
                    if r["published_at"] is not None
                    else r
                    for r in result
                ]

        logger.info(
            "op=offline_fetch place_id=%s reviews=%d file=%s",
            place_id,
            len(result),
            entry["reviews_file"],
        )
        return result
