"""End-to-end test for the full core workflow.

Requires a running backend (e.g. via `make up`).
Set BASE_URL env var if the backend is not at http://localhost:8000.

Works with any REVIEW_PROVIDER setting:
- mock: uses sample data, all assertions run
- outscraper: only runs full assertions if the provider returns reviews

Run:
    python -m pytest tests/e2e/ -v
"""

import os
import uuid

import httpx
import pytest

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API = f"{BASE_URL}/api"


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    with httpx.Client(base_url=API, timeout=30) as c:
        yield c


def test_full_flow(client: httpx.Client):
    """Register → login → add business → fetch reviews → analyze → dashboard."""
    email = f"e2e-{uuid.uuid4().hex[:8]}@test.com"
    password = "testpass123"

    # ── Register ──
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code == 201, f"Register failed: {r.text}"

    # ── Login ──
    r = client.post("/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # ── Create business ──
    r = client.post(
        "/businesses",
        json={
            "google_maps_url": "https://www.google.com/maps/place/Test+Business/@0,0,17z/data=!4m2!3m1!1s0x0:0x1",
            "business_type": "restaurant",
        },
        headers=headers,
    )
    assert r.status_code == 201, f"Create business failed: {r.text}"
    biz = r.json()
    biz_id = biz["id"]
    assert biz["business_type"] == "restaurant"
    assert biz["total_reviews"] == 0

    # ── Fetch reviews ──
    r = client.post(f"/businesses/{biz_id}/fetch-reviews", headers=headers)
    assert r.status_code == 200, f"Fetch reviews failed: {r.text}"
    reviews = r.json()
    assert isinstance(reviews, list)

    if len(reviews) == 0:
        pytest.skip(
            "Provider returned no reviews (expected with outscraper + test URL). "
            "Skipping analysis and dashboard assertions."
        )

    # ── Verify review shape ──
    first = reviews[0]
    assert "external_id" in first
    assert "source" in first
    assert "rating" in first

    # ── Run analysis ──
    r = client.post(f"/businesses/{biz_id}/analyze", headers=headers)
    assert r.status_code == 200, f"Analyze failed: {r.text}"
    analysis = r.json()
    assert analysis["summary"]
    assert isinstance(analysis["top_complaints"], list)
    assert isinstance(analysis["top_praise"], list)
    assert isinstance(analysis["action_items"], list)
    assert isinstance(analysis["risk_areas"], list)
    assert analysis["recommended_focus"]

    # ── Verify dashboard ──
    r = client.get(f"/businesses/{biz_id}/dashboard", headers=headers)
    assert r.status_code == 200, f"Dashboard failed: {r.text}"
    d = r.json()
    assert d["business_name"]
    assert d["business_type"] == "restaurant"
    assert d["avg_rating"] is not None
    assert d["total_reviews"] > 0
    assert len(d["top_complaints"]) > 0
    assert len(d["top_praise"]) > 0
    assert d["ai_summary"]
    assert len(d["action_items"]) > 0
    assert len(d["risk_areas"]) > 0
    assert d["recommended_focus"]

    # ── Refresh reviews should clear analysis ──
    r = client.post(f"/businesses/{biz_id}/fetch-reviews", headers=headers)
    assert r.status_code == 200

    r = client.get(f"/businesses/{biz_id}/dashboard", headers=headers)
    assert r.status_code == 200
    d = r.json()
    assert d["ai_summary"] is None
    assert d["top_complaints"] == []
    assert d["action_items"] == []
    assert d["recommended_focus"] is None
