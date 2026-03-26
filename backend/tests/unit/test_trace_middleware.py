"""T1.2 — Unit tests for TraceMiddleware header injection and propagation.

Tests cover:
- Middleware generates X-Trace-Id when none provided
- Middleware echoes back a client-supplied X-Trace-Id
- X-Trace-Id is present on all responses (including errors)
- Trace ID stored in contextvars so downstream code can read it
- No headers injected when DEBUG_TRACE is off
"""

import os

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_app(debug_trace: bool = True) -> FastAPI:
    """Create a minimal FastAPI app with TraceMiddleware for testing."""
    from app.tracing import TraceMiddleware, get_current_trace_id

    app = FastAPI()

    if debug_trace:
        app.add_middleware(TraceMiddleware)

    @app.get("/ping")
    def ping():
        return {"trace_id": get_current_trace_id()}

    @app.get("/error")
    def error():
        raise ValueError("boom")

    return app


# ---------------------------------------------------------------------------
# T1.2a — header injection
# ---------------------------------------------------------------------------

class TestTraceMiddlewareInjection:
    def test_response_has_trace_id_header(self):
        client = TestClient(_make_app(debug_trace=True), raise_server_exceptions=False)
        r = client.get("/ping")
        assert "x-trace-id" in r.headers

    def test_generated_trace_id_is_nonempty(self):
        client = TestClient(_make_app(debug_trace=True), raise_server_exceptions=False)
        r = client.get("/ping")
        assert len(r.headers["x-trace-id"]) > 8

    def test_client_supplied_trace_id_echoed(self):
        client = TestClient(_make_app(debug_trace=True), raise_server_exceptions=False)
        r = client.get("/ping", headers={"x-trace-id": "my-custom-id"})
        assert r.headers["x-trace-id"] == "my-custom-id"

    def test_trace_id_consistent_in_body(self):
        """get_current_trace_id() inside the handler matches the response header."""
        client = TestClient(_make_app(debug_trace=True), raise_server_exceptions=False)
        r = client.get("/ping")
        assert r.json()["trace_id"] == r.headers["x-trace-id"]

    def test_trace_id_on_error_response(self):
        client = TestClient(_make_app(debug_trace=True), raise_server_exceptions=False)
        r = client.get("/error")
        assert "x-trace-id" in r.headers


# ---------------------------------------------------------------------------
# T1.2b — disabled (DEBUG_TRACE off)
# ---------------------------------------------------------------------------

class TestTraceMiddlewareDisabled:
    def test_no_trace_header_when_disabled(self):
        client = TestClient(_make_app(debug_trace=False), raise_server_exceptions=False)
        r = client.get("/ping")
        assert "x-trace-id" not in r.headers

    def test_get_current_trace_id_returns_none_when_disabled(self):
        client = TestClient(_make_app(debug_trace=False), raise_server_exceptions=False)
        r = client.get("/ping")
        assert r.json()["trace_id"] is None


# ---------------------------------------------------------------------------
# T1.2c — contextvar isolation across requests
# ---------------------------------------------------------------------------

class TestTraceMiddlewareContextIsolation:
    def test_each_request_gets_unique_trace_id(self):
        client = TestClient(_make_app(debug_trace=True), raise_server_exceptions=False)
        ids = {client.get("/ping").headers["x-trace-id"] for _ in range(5)}
        assert len(ids) == 5  # all unique
