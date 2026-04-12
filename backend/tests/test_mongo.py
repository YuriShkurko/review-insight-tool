"""Tests for app.mongo — graceful no-op when MONGO_URI is empty."""

from datetime import UTC, datetime

from app.mongo import (
    archive_analysis,
    cache_comparison,
    get_analysis_history,
    get_cached_comparison,
    store_raw_provider_response,
)


def test_archive_analysis_noop():
    """archive_analysis does nothing when MongoDB is not configured."""
    archive_analysis(
        business_id="fake-id",
        summary="test summary",
        top_complaints=[{"label": "slow", "count": 3}],
        top_praise=[{"label": "friendly", "count": 5}],
        action_items=["hire more staff"],
        risk_areas=["wait times"],
        recommended_focus="speed",
        created_at=datetime.now(UTC),
    )  # Should not raise


def test_get_analysis_history_returns_empty():
    assert get_analysis_history("fake-id") == []


def test_get_cached_comparison_returns_none():
    assert get_cached_comparison("fake-id", ["comp-1"]) is None


def test_cache_comparison_noop():
    cache_comparison(
        business_id="fake-id",
        competitor_ids=["comp-1"],
        target_snapshot={"name": "test"},
        competitor_snapshots=[],
        comparison_summary="",
        strengths=[],
        weaknesses=[],
        opportunities=[],
    )  # Should not raise


def test_store_raw_response_noop():
    store_raw_provider_response(
        business_id="fake-id",
        provider="test",
        place_id="place123",
        raw_response={"data": []},
        review_count=0,
    )  # Should not raise
