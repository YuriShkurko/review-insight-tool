"""T2.1–T2.5 — Unit tests for the 5 new MCP dipstick tools.

All tools are called directly as Python functions (not via MCP transport).
Each test constructs a mock/stub TraceContext so the tools have data to query.

Tools under test:
    trace_journey(trace_id)    — ordered spans for one trace
    health_probe()             — component liveness map
    recent_traces(limit)       — newest-first trace summaries
    mutation_log(entity_id)    — spans where mutation=True for an entity
    llm_call_log(business_id)  — LLM spans filtered by business_id
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — build a populated TraceContext without hitting the real module-level
# singleton so tests remain hermetic.
# ---------------------------------------------------------------------------

def _make_ctx():
    from app.tracing import TraceContext
    ctx = TraceContext(max_traces=50, max_spans_per_trace=50, enabled=True)
    return ctx


def _seed_trace(ctx, trace_id: str, endpoint: str, spans: list[dict]) -> None:
    """Add a trace with pre-built spans to ctx."""
    ctx.add_trace(trace_id, endpoint=endpoint)
    for sp in spans:
        ctx.add_span(
            trace_id,
            name=sp["name"],
            duration_ms=sp.get("duration_ms", 1.0),
            success=sp.get("success", True),
            metadata=sp.get("metadata", {}),
        )


# ---------------------------------------------------------------------------
# Import the tool functions under test — they don't exist yet so the import
# raises ImportError, making all tests in this file fail (RED) until T2.6-T2.10
# implement them.
# ---------------------------------------------------------------------------

def _get_tools():
    from debug.dipstick import (
        get_trace_journey,
        get_health_probe,
        get_recent_traces,
        get_mutation_log,
        get_llm_call_log,
    )
    return get_trace_journey, get_health_probe, get_recent_traces, get_mutation_log, get_llm_call_log


# ---------------------------------------------------------------------------
# T2.1 — trace_journey
# ---------------------------------------------------------------------------

class TestTraceJourney:
    def test_returns_ordered_spans_for_trace(self):
        ctx = _make_ctx()
        _seed_trace(ctx, "tid-1", "/api/analyze", [
            {"name": "route_enter", "duration_ms": 1},
            {"name": "db_query",    "duration_ms": 5},
            {"name": "llm_call",    "duration_ms": 800},
            {"name": "route_exit",  "duration_ms": 1},
        ])
        get_trace_journey, *_ = _get_tools()
        result = get_trace_journey(ctx, "tid-1")
        assert result["trace_id"] == "tid-1"
        names = [s["name"] for s in result["spans"]]
        assert names == ["route_enter", "db_query", "llm_call", "route_exit"]

    def test_each_span_has_required_fields(self):
        ctx = _make_ctx()
        _seed_trace(ctx, "tid-1", "/api/test", [{"name": "db_query", "duration_ms": 10}])
        get_trace_journey, *_ = _get_tools()
        result = get_trace_journey(ctx, "tid-1")
        span = result["spans"][0]
        assert "name" in span
        assert "duration_ms" in span
        assert "success" in span

    def test_missing_trace_returns_not_found(self):
        ctx = _make_ctx()
        get_trace_journey, *_ = _get_tools()
        result = get_trace_journey(ctx, "ghost-id")
        assert "error" in result

    def test_endpoint_included_in_result(self):
        ctx = _make_ctx()
        ctx.add_trace("tid-1", endpoint="/api/businesses/1/analyze")
        get_trace_journey, *_ = _get_tools()
        result = get_trace_journey(ctx, "tid-1")
        assert result["endpoint"] == "/api/businesses/1/analyze"


# ---------------------------------------------------------------------------
# T2.2 — health_probe
# ---------------------------------------------------------------------------

class TestHealthProbe:
    def test_returns_db_status_key(self):
        _, get_health_probe, *_ = _get_tools()
        result = get_health_probe()
        assert "db" in result

    def test_db_ok_on_successful_ping(self):
        _, get_health_probe, *_ = _get_tools()
        with patch("debug.dipstick._db_ping", return_value=True):
            result = get_health_probe()
        assert result["db"] == "ok"

    def test_db_error_on_failed_ping(self):
        _, get_health_probe, *_ = _get_tools()
        with patch("debug.dipstick._db_ping", return_value=False):
            result = get_health_probe()
        assert result["db"] == "error"

    def test_returns_provider_status(self):
        _, get_health_probe, *_ = _get_tools()
        result = get_health_probe()
        assert "review_provider" in result

    def test_returns_trace_buffer_status(self):
        _, get_health_probe, *_ = _get_tools()
        result = get_health_probe()
        assert "trace_buffer" in result


# ---------------------------------------------------------------------------
# T2.3 — recent_traces
# ---------------------------------------------------------------------------

class TestRecentTraces:
    def test_returns_list_newest_first(self):
        ctx = _make_ctx()
        for i in range(5):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
            time.sleep(0.001)
        _, _, get_recent_traces, *_ = _get_tools()
        result = get_recent_traces(ctx, limit=10)
        ids = [t["trace_id"] for t in result["traces"]]
        assert ids[0] == "tid-4"  # most recent first

    def test_limit_respected(self):
        ctx = _make_ctx()
        for i in range(10):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        _, _, get_recent_traces, *_ = _get_tools()
        result = get_recent_traces(ctx, limit=3)
        assert len(result["traces"]) == 3

    def test_each_trace_has_required_fields(self):
        ctx = _make_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")
        ctx.add_span("tid-1", name="db_query", duration_ms=5.0, success=True)
        _, _, get_recent_traces, *_ = _get_tools()
        result = get_recent_traces(ctx, limit=5)
        t = result["traces"][0]
        assert "trace_id" in t
        assert "endpoint" in t
        assert "span_count" in t

    def test_empty_context_returns_empty_list(self):
        ctx = _make_ctx()
        _, _, get_recent_traces, *_ = _get_tools()
        result = get_recent_traces(ctx, limit=10)
        assert result["traces"] == []


# ---------------------------------------------------------------------------
# T2.4 — mutation_log
# ---------------------------------------------------------------------------

class TestMutationLog:
    def test_returns_spans_for_entity(self):
        ctx = _make_ctx()
        _seed_trace(ctx, "tid-1", "/api/test", [
            {"name": "db_write", "metadata": {"entity_id": "biz-1", "mutation": True}},
            {"name": "db_read",  "metadata": {"entity_id": "biz-1", "mutation": False}},
        ])
        *_, get_mutation_log, _ = _get_tools()
        result = get_mutation_log(ctx, entity_id="biz-1")
        # Only the write span, not the read
        assert len(result["mutations"]) == 1
        assert result["mutations"][0]["name"] == "db_write"

    def test_returns_empty_for_unknown_entity(self):
        ctx = _make_ctx()
        *_, get_mutation_log, _ = _get_tools()
        result = get_mutation_log(ctx, entity_id="ghost")
        assert result["mutations"] == []

    def test_includes_trace_id_per_mutation(self):
        ctx = _make_ctx()
        _seed_trace(ctx, "tid-1", "/api/test", [
            {"name": "db_write", "metadata": {"entity_id": "biz-1", "mutation": True}},
        ])
        *_, get_mutation_log, _ = _get_tools()
        result = get_mutation_log(ctx, entity_id="biz-1")
        assert result["mutations"][0]["trace_id"] == "tid-1"

    def test_spans_across_multiple_traces(self):
        ctx = _make_ctx()
        for i in range(3):
            _seed_trace(ctx, f"tid-{i}", "/api/test", [
                {"name": "db_write", "metadata": {"entity_id": "biz-99", "mutation": True}},
            ])
        *_, get_mutation_log, _ = _get_tools()
        result = get_mutation_log(ctx, entity_id="biz-99")
        assert len(result["mutations"]) == 3


# ---------------------------------------------------------------------------
# T2.5 — llm_call_log
# ---------------------------------------------------------------------------

class TestLlmCallLog:
    def test_returns_llm_spans_for_business(self):
        ctx = _make_ctx()
        _seed_trace(ctx, "tid-1", "/api/analyze", [
            {"name": "llm_call", "duration_ms": 750, "metadata": {"business_id": "biz-1"}},
            {"name": "db_query", "duration_ms": 5,   "metadata": {"business_id": "biz-1"}},
        ])
        *_, get_llm_call_log = _get_tools()
        result = get_llm_call_log(ctx, business_id="biz-1")
        assert len(result["llm_calls"]) == 1
        assert result["llm_calls"][0]["name"] == "llm_call"

    def test_returns_empty_for_unknown_business(self):
        ctx = _make_ctx()
        *_, get_llm_call_log = _get_tools()
        result = get_llm_call_log(ctx, business_id="ghost")
        assert result["llm_calls"] == []

    def test_each_entry_has_duration_and_trace_id(self):
        ctx = _make_ctx()
        _seed_trace(ctx, "tid-1", "/api/analyze", [
            {"name": "llm_call", "duration_ms": 800, "metadata": {"business_id": "biz-1"}},
        ])
        *_, get_llm_call_log = _get_tools()
        result = get_llm_call_log(ctx, business_id="biz-1")
        entry = result["llm_calls"][0]
        assert "duration_ms" in entry
        assert "trace_id" in entry

    def test_multiple_llm_calls_across_traces(self):
        ctx = _make_ctx()
        for i in range(4):
            _seed_trace(ctx, f"tid-{i}", "/api/analyze", [
                {"name": "llm_call", "duration_ms": 300 + i * 100, "metadata": {"business_id": "biz-42"}},
            ])
        *_, get_llm_call_log = _get_tools()
        result = get_llm_call_log(ctx, business_id="biz-42")
        assert len(result["llm_calls"]) == 4
