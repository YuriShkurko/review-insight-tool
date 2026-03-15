"""Integration tests for the core business + review + analysis flow."""

from fastapi.testclient import TestClient

from .conftest import SAMPLE_MAPS_URL


def test_full_business_lifecycle(client: TestClient, auth_headers: dict):
    """Register -> add business -> fetch reviews -> analyze -> dashboard."""

    # Create business
    r = client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "bar"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    biz = r.json()
    biz_id = biz["id"]
    assert biz["business_type"] == "bar"
    assert biz["total_reviews"] == 0

    # List businesses — should contain the new one
    r = client.get("/api/businesses", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Fetch reviews (mock provider)
    r = client.post(f"/api/businesses/{biz_id}/fetch-reviews", headers=auth_headers)
    assert r.status_code == 200
    reviews = r.json()
    assert len(reviews) > 0

    # Run analysis (mock LLM)
    r = client.post(f"/api/businesses/{biz_id}/analyze", headers=auth_headers)
    assert r.status_code == 200
    analysis = r.json()
    assert analysis["summary"]
    assert isinstance(analysis["top_complaints"], list)
    assert isinstance(analysis["top_praise"], list)
    assert isinstance(analysis["action_items"], list)
    assert isinstance(analysis["risk_areas"], list)
    assert analysis["recommended_focus"]

    # Dashboard has all fields
    r = client.get(f"/api/businesses/{biz_id}/dashboard", headers=auth_headers)
    assert r.status_code == 200
    d = r.json()
    assert d["business_name"]
    assert d["business_type"] == "bar"
    assert d["total_reviews"] > 0
    assert d["ai_summary"]
    assert len(d["top_complaints"]) > 0
    assert d["recommended_focus"]
    assert d["analysis_created_at"] is not None


def test_analyze_without_reviews_fails(client: TestClient, auth_headers: dict):
    """Running analysis before fetching reviews returns 400."""
    r = client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "restaurant"},
        headers=auth_headers,
    )
    biz_id = r.json()["id"]

    r = client.post(f"/api/businesses/{biz_id}/analyze", headers=auth_headers)
    assert r.status_code == 400
    assert "reviews" in r.json()["detail"].lower()


def test_refresh_clears_stale_analysis(client: TestClient, auth_headers: dict):
    """Fetching reviews again should clear old analysis."""

    r = client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "cafe"},
        headers=auth_headers,
    )
    biz_id = r.json()["id"]

    # Fetch + analyze
    client.post(f"/api/businesses/{biz_id}/fetch-reviews", headers=auth_headers)
    client.post(f"/api/businesses/{biz_id}/analyze", headers=auth_headers)

    # Verify analysis exists
    r = client.get(f"/api/businesses/{biz_id}/dashboard", headers=auth_headers)
    assert r.json()["ai_summary"] is not None

    # Refresh reviews
    client.post(f"/api/businesses/{biz_id}/fetch-reviews", headers=auth_headers)

    # Analysis should be cleared
    r = client.get(f"/api/businesses/{biz_id}/dashboard", headers=auth_headers)
    d = r.json()
    assert d["ai_summary"] is None
    assert d["top_complaints"] == []
    assert d["action_items"] == []
    assert d["recommended_focus"] is None


def test_duplicate_business_returns_409(client: TestClient, auth_headers: dict):
    """Adding the same business twice returns 409."""
    client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "restaurant"},
        headers=auth_headers,
    )
    r = client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "restaurant"},
        headers=auth_headers,
    )
    assert r.status_code == 409


def test_business_not_found_returns_404(client: TestClient, auth_headers: dict):
    """Accessing a non-existent business returns 404."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    r = client.get(f"/api/businesses/{fake_id}/dashboard", headers=auth_headers)
    assert r.status_code == 404
