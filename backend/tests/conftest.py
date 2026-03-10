"""Shared fixtures for backend tests."""

import uuid
from datetime import datetime, timezone

import pytest


@pytest.fixture()
def sample_place_id() -> str:
    return "0x151d4b85554f2dc1:0xd8359c5dcd553b"


@pytest.fixture()
def sample_business_id() -> uuid.UUID:
    return uuid.uuid4()


@pytest.fixture()
def sample_raw_reviews() -> list[dict]:
    """Minimal raw reviews matching the NormalizedReview shape."""
    return [
        {
            "external_id": "test_001",
            "source": "test",
            "author": "Alice",
            "rating": 5,
            "text": "Fantastic place!",
            "published_at": datetime(2025, 6, 1, tzinfo=timezone.utc),
        },
        {
            "external_id": "test_002",
            "source": "test",
            "author": "Bob",
            "rating": 2,
            "text": "Too slow.",
            "published_at": datetime(2025, 5, 15, tzinfo=timezone.utc),
        },
        {
            "external_id": "test_003",
            "source": "test",
            "author": None,
            "rating": 4,
            "text": None,
            "published_at": None,
        },
    ]
