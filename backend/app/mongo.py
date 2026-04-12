"""MongoDB client for polyglot persistence (optional).

When MONGO_URI is empty or connection fails, all public functions
return None / empty results.  The main Postgres flow is never affected.

Collections
-----------
analysis_history          Versioned analysis snapshots (permanent)
comparison_cache          Cached competitor comparisons  (TTL)
raw_provider_responses    Raw API payloads for audit     (TTL)
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from app.config import settings

logger = logging.getLogger(__name__)

_client = None
_db = None


def _init_mongo() -> None:
    """Lazily initialise the MongoDB client on first use."""
    global _client, _db
    if _client is not None or not settings.MONGO_URI:
        return
    try:
        from pymongo import MongoClient

        _client = MongoClient(
            settings.MONGO_URI,
            serverSelectionTimeoutMS=3000,
            connectTimeoutMS=3000,
        )
        _client.admin.command("ping")
        _db = _client[settings.MONGO_DB_NAME]
        _ensure_indexes()
        logger.info("op=mongo_init success=true db=%s", settings.MONGO_DB_NAME)
    except Exception as exc:
        logger.warning("op=mongo_init success=false error=%s (MongoDB features disabled)", exc)
        _client = None
        _db = None


def _ensure_indexes() -> None:
    """Create TTL and query indexes (idempotent)."""
    if _db is None:
        return
    _db.analysis_history.create_index([("business_id", 1), ("version", -1)])
    _db.comparison_cache.create_index([("business_id", 1)])
    _db.comparison_cache.create_index("expires_at", expireAfterSeconds=0)
    _db.raw_provider_responses.create_index([("business_id", 1)])
    _db.raw_provider_responses.create_index("expires_at", expireAfterSeconds=0)


def _get_db():
    """Return the MongoDB database handle, or None."""
    _init_mongo()
    return _db


# ── Analysis history ────────────────────────────────────────────


def archive_analysis(
    business_id: str,
    summary: str,
    top_complaints: list,
    top_praise: list,
    action_items: list,
    risk_areas: list,
    recommended_focus: str,
    created_at: datetime | None = None,
) -> None:
    """Archive the current analysis snapshot before it gets overwritten."""
    db = _get_db()
    if db is None:
        return
    try:
        latest = db.analysis_history.find_one(
            {"business_id": business_id},
            sort=[("version", -1)],
            projection={"version": 1},
        )
        next_version = (latest["version"] + 1) if latest else 1

        db.analysis_history.insert_one(
            {
                "business_id": business_id,
                "version": next_version,
                "summary": summary,
                "top_complaints": top_complaints,
                "top_praise": top_praise,
                "action_items": action_items,
                "risk_areas": risk_areas,
                "recommended_focus": recommended_focus,
                "created_at": created_at or datetime.now(UTC),
                "archived_at": datetime.now(UTC),
            }
        )
        logger.info(
            "op=archive_analysis business_id=%s version=%d",
            business_id,
            next_version,
        )
    except Exception as exc:
        logger.warning("op=archive_analysis success=false error=%s", exc)


def get_analysis_history(business_id: str, limit: int = 20) -> list[dict]:
    """Return previous analysis versions for a business, newest first."""
    db = _get_db()
    if db is None:
        return []
    try:
        cursor = (
            db.analysis_history.find({"business_id": business_id}, {"_id": 0})
            .sort("version", -1)
            .limit(limit)
        )
        return list(cursor)
    except Exception as exc:
        logger.warning("op=get_analysis_history success=false error=%s", exc)
        return []


# ── Comparison cache ────────────────────────────────────────────


def get_cached_comparison(
    business_id: str,
    competitor_ids: list[str],
) -> dict | None:
    """Return a cached comparison if fresh, else None."""
    db = _get_db()
    if db is None:
        return None
    try:
        doc = db.comparison_cache.find_one(
            {
                "business_id": business_id,
                "competitor_ids": sorted(competitor_ids),
                "expires_at": {"$gt": datetime.now(UTC)},
            },
            {"_id": 0},
        )
        return doc
    except Exception as exc:
        logger.warning("op=get_cached_comparison success=false error=%s", exc)
        return None


def cache_comparison(
    business_id: str,
    competitor_ids: list[str],
    target_snapshot: dict,
    competitor_snapshots: list[dict],
    comparison_summary: str,
    strengths: list[str],
    weaknesses: list[str],
    opportunities: list[str],
) -> None:
    """Cache a comparison result with TTL."""
    db = _get_db()
    if db is None:
        return
    try:
        now = datetime.now(UTC)
        ttl_hours = settings.COMPARISON_CACHE_TTL_HOURS
        doc = {
            "business_id": business_id,
            "competitor_ids": sorted(competitor_ids),
            "target_snapshot": target_snapshot,
            "competitor_snapshots": competitor_snapshots,
            "comparison_summary": comparison_summary,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "opportunities": opportunities,
            "created_at": now,
            "expires_at": now + timedelta(hours=ttl_hours),
        }
        db.comparison_cache.replace_one(
            {
                "business_id": business_id,
                "competitor_ids": sorted(competitor_ids),
            },
            doc,
            upsert=True,
        )
        logger.info(
            "op=cache_comparison business_id=%s ttl_hours=%d",
            business_id,
            ttl_hours,
        )
    except Exception as exc:
        logger.warning("op=cache_comparison success=false error=%s", exc)


# ── Raw provider responses ──────────────────────────────────────


def store_raw_provider_response(
    business_id: str,
    provider: str,
    place_id: str,
    raw_response: Any,
    review_count: int,
) -> None:
    """Store raw API response for debugging/audit."""
    db = _get_db()
    if db is None:
        return
    try:
        now = datetime.now(UTC)
        ttl_days = settings.RAW_RESPONSE_TTL_DAYS
        db.raw_provider_responses.insert_one(
            {
                "business_id": business_id,
                "provider": provider,
                "place_id": place_id,
                "raw_response": raw_response,
                "review_count": review_count,
                "fetched_at": now,
                "expires_at": now + timedelta(days=ttl_days),
            }
        )
        logger.info(
            "op=store_raw_response business_id=%s provider=%s reviews=%d",
            business_id,
            provider,
            review_count,
        )
    except Exception as exc:
        logger.warning("op=store_raw_response success=false error=%s", exc)
