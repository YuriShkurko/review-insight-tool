"""Integration tests proving the ScriptedProvider drives the real /agent/chat."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .conftest import SAMPLE_MAPS_URL
from .test_agent_flow import _parse_sse

# ---------------------------------------------------------------------------
# Fresh app per test: TESTING / LLM_PROVIDER are read at create_app() time,
# so we can't rely on the shared `client` fixture (which builds an app with
# TESTING=false). Each helper builds an isolated in-memory app.
# ---------------------------------------------------------------------------


def _build_testing_app(*, testing: bool):
    import app.config as config_mod
    import app.database as db_mod
    from app.database import Base, get_db
    from app.llm import factory as factory_mod
    from app.llm.scripted import reset_scripted_provider

    reset_scripted_provider()

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_fk(dbapi_conn, _rec):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    import app.models

    Base.metadata.create_all(bind=engine)
    db_mod.engine = engine

    object.__setattr__(config_mod.settings, "REVIEW_PROVIDER", "mock")
    object.__setattr__(config_mod.settings, "OPENAI_API_KEY", "")
    object.__setattr__(config_mod.settings, "LLM_PROVIDER", "scripted")
    object.__setattr__(config_mod.settings, "TESTING", testing)
    object.__setattr__(config_mod.settings, "AGENT_SCRIPT_PATH", "")

    # Force the executor to consult the freshly-configured factory.
    import app.agent.executor as executor_mod

    executor_mod.get_llm_provider = factory_mod.get_llm_provider

    from app.main import create_app

    app = create_app()

    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def _override_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_db
    return app, engine


@pytest.fixture()
def testing_client():
    app, engine = _build_testing_app(testing=True)
    with TestClient(app) as c:
        yield c
    engine.dispose()


@pytest.fixture()
def production_like_client():
    """TESTING=false — used to assert /api/test/* is unmounted."""
    app, engine = _build_testing_app(testing=False)
    with TestClient(app) as c:
        yield c
    engine.dispose()


def _register(client: TestClient) -> dict[str, str]:
    import uuid as _u

    email = f"st-{_u.uuid4().hex[:8]}@test.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "testpass123"})
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_biz(client: TestClient, headers: dict) -> str:
    r = client.post(
        "/api/businesses",
        json={"google_maps_url": SAMPLE_MAPS_URL, "business_type": "cafe"},
        headers=headers,
    )
    assert r.status_code == 201
    return r.json()["id"]


# ---------------------------------------------------------------------------
# Test endpoint gating
# ---------------------------------------------------------------------------


def test_test_endpoint_unmounted_when_testing_false(production_like_client: TestClient):
    """/api/test/agent/script must not exist when TESTING=false (404, not 422/204)."""
    r = production_like_client.post(
        "/api/test/agent/script",
        json={"script": [{"text": "x", "tool_calls": []}]},
    )
    assert r.status_code == 404, (
        f"test-only route must be unmounted when TESTING is false; got {r.status_code}"
    )


def test_test_endpoint_accepts_script_when_testing_true(testing_client: TestClient):
    r = testing_client.post(
        "/api/test/agent/script",
        json={"script": [{"text": "ack", "tool_calls": []}]},
    )
    assert r.status_code == 204


def test_test_endpoint_rejects_malformed_body_with_422(testing_client: TestClient):
    r = testing_client.post("/api/test/agent/script", json={"not_script": []})
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# End-to-end: ScriptedProvider drives /agent/chat through a tool call
# ---------------------------------------------------------------------------


def test_scripted_provider_drives_agent_chat_through_pin_widget(
    testing_client: TestClient,
):
    headers = _register(testing_client)
    biz_id = _make_biz(testing_client, headers)

    fixture = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "agent_scripts"
        / "add_widget_with_data.json"
    )
    script = json.loads(fixture.read_text(encoding="utf-8"))

    # Inject the script via the test endpoint (mirrors what Playwright will do).
    r = testing_client.post("/api/test/agent/script", json={"script": script})
    assert r.status_code == 204

    r = testing_client.post(
        f"/api/businesses/{biz_id}/agent/chat",
        json={"message": "Show me a rating distribution"},
        headers=headers,
    )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    types = [e["type"] for e in events]
    assert "tool_call" in types
    assert "tool_result" in types
    assert "workspace_event" in types
    assert "done" in types

    pin_result = next(
        e for e in events if e["type"] == "tool_result" and e["data"].get("name") == "pin_widget"
    )
    assert pin_result["data"]["result"]["pinned"] is True

    workspace_event = next(e for e in events if e["type"] == "workspace_event")
    assert workspace_event["data"]["action"] == "widget_added"
    assert workspace_event["data"]["widget"]["widget_type"] == "bar_chart"

    # Verify the widget actually persisted
    r = testing_client.get(f"/api/businesses/{biz_id}/agent/workspace", headers=headers)
    assert r.status_code == 200
    widgets = r.json()
    assert len(widgets) == 1
    assert widgets[0]["widget_type"] == "bar_chart"
    assert widgets[0]["title"] == "Rating distribution"


def test_scripted_exhaustion_surfaces_as_error_event(testing_client: TestClient):
    """If the script runs out mid-loop, the executor catches the RuntimeError.

    The current executor wraps provider exceptions with a generic 'AI call
    failed' text_delta. We assert that channel — not the exact text — so a
    future error-event upgrade doesn't break this test.
    """
    headers = _register(testing_client)
    biz_id = _make_biz(testing_client, headers)

    # One-turn script that requests a tool call but never provides the
    # follow-up assistant turn — exhaustion fires on iteration 2.
    script = [
        {
            "text": "",
            "tool_calls": [{"name": "get_dashboard", "arguments": {}}],
        }
    ]
    r = testing_client.post("/api/test/agent/script", json={"script": script})
    assert r.status_code == 204

    r = testing_client.post(
        f"/api/businesses/{biz_id}/agent/chat",
        json={"message": "what's my dashboard"},
        headers=headers,
    )
    assert r.status_code == 200
    events = _parse_sse(r.text)
    text_events = [e for e in events if e["type"] == "text_delta"]
    combined = " ".join(e["data"].get("text", "") for e in text_events).lower()
    assert "ai call failed" in combined or "failed" in combined
