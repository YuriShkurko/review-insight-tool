"""Integration tests for competitor linking and the promotion flow."""

from fastapi.testclient import TestClient

from .conftest import SAMPLE_MAPS_URL, SAMPLE_MAPS_URL_2, SAMPLE_MAPS_URL_3


def _create_business(client: TestClient, headers: dict, url: str = SAMPLE_MAPS_URL) -> str:
    r = client.post(
        "/api/businesses",
        json={"google_maps_url": url, "business_type": "bar"},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_add_and_list_competitors(client: TestClient, auth_headers: dict):
    """Link a competitor and verify it appears in the list."""
    biz_id = _create_business(client, auth_headers)

    # Add competitor
    r = client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )
    assert r.status_code == 201
    comp = r.json()
    assert comp["has_reviews"] is False
    assert comp["has_analysis"] is False

    # List competitors
    r = client.get(f"/api/businesses/{biz_id}/competitors", headers=auth_headers)
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_competitor_not_in_main_list(client: TestClient, auth_headers: dict):
    """Competitor-only businesses must not appear in GET /businesses."""
    biz_id = _create_business(client, auth_headers)

    client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )

    r = client.get("/api/businesses", headers=auth_headers)
    ids = [b["id"] for b in r.json()]
    assert biz_id in ids
    assert len(ids) == 1


def test_remove_competitor(client: TestClient, auth_headers: dict):
    """Removing a competitor link returns 204 and clears the list."""
    biz_id = _create_business(client, auth_headers)

    r = client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )
    comp_biz_id = r.json()["business"]["id"]

    r = client.delete(
        f"/api/businesses/{biz_id}/competitors/{comp_biz_id}",
        headers=auth_headers,
    )
    assert r.status_code == 204

    r = client.get(f"/api/businesses/{biz_id}/competitors", headers=auth_headers)
    assert len(r.json()) == 0


def test_duplicate_competitor_link_no_error(client: TestClient, auth_headers: dict):
    """Adding the same competitor twice returns the existing link, not an error."""
    biz_id = _create_business(client, auth_headers)

    r1 = client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )
    assert r1.status_code == 201

    r2 = client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )
    assert r2.status_code == 201
    assert r1.json()["link_id"] == r2.json()["link_id"]

    # Only one link exists
    r = client.get(f"/api/businesses/{biz_id}/competitors", headers=auth_headers)
    assert len(r.json()) == 1


def test_self_link_rejected(client: TestClient, auth_headers: dict):
    """A business cannot be linked as its own competitor."""
    biz_id = _create_business(client, auth_headers)

    r = client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "bar"},
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "own competitor" in r.json()["detail"].lower()


def test_promotion_competitor_to_regular(client: TestClient, auth_headers: dict):
    """Adding a competitor-only business from the main form promotes it."""
    biz_id = _create_business(client, auth_headers)

    # Add as competitor first
    client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )

    # Competitor-only: not in main list
    r = client.get("/api/businesses", headers=auth_headers)
    assert len(r.json()) == 1

    # Now add the same place from the main form — should promote
    r = client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )
    assert r.status_code == 201

    # Now both appear in main list
    r = client.get("/api/businesses", headers=auth_headers)
    assert len(r.json()) == 2


def test_comparison_without_analysis_fails(client: TestClient, auth_headers: dict):
    """Comparison without analysis on the target returns 400."""
    biz_id = _create_business(client, auth_headers)

    client.post(
        f"/api/businesses/{biz_id}/competitors",
        json={"google_maps_url": SAMPLE_MAPS_URL_2, "business_type": "bar"},
        headers=auth_headers,
    )

    r = client.post(
        f"/api/businesses/{biz_id}/competitors/comparison",
        headers=auth_headers,
    )
    assert r.status_code == 400
    assert "analysis" in r.json()["detail"].lower()
