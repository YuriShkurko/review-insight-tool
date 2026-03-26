"""T1.1 — Unit tests for TraceContext ring buffer.

Tests cover:
- add_trace / get_trace round-trip
- add_span appends to the right trace
- Ring eviction at capacity (oldest dropped, size stays at MAX_TRACES)
- Thread safety: concurrent writers do not corrupt the buffer
- list_recent returns newest-first
- No-op behaviour when DEBUG_TRACE is off
"""

import threading
import time

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_trace(trace_id: str = "tid-1", endpoint: str = "/api/test") -> dict:
    return {"trace_id": trace_id, "endpoint": endpoint, "started_at": time.time()}


def _make_span(name: str = "db_query", duration_ms: float = 5.0) -> dict:
    return {
        "name": name,
        "started_at": time.time(),
        "duration_ms": duration_ms,
        "success": True,
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# T1.1a — basic add / get
# ---------------------------------------------------------------------------

class TestTraceContextBasic:
    def test_add_and_get_trace(self):
        from app.tracing import TraceContext
        ctx = TraceContext()
        ctx.add_trace("tid-1", endpoint="/api/test")
        trace = ctx.get_trace("tid-1")
        assert trace is not None
        assert trace["trace_id"] == "tid-1"
        assert trace["endpoint"] == "/api/test"

    def test_get_missing_trace_returns_none(self):
        from app.tracing import TraceContext
        ctx = TraceContext()
        assert ctx.get_trace("nonexistent") is None

    def test_add_span_to_trace(self):
        from app.tracing import TraceContext
        ctx = TraceContext()
        ctx.add_trace("tid-1", endpoint="/api/test")
        ctx.add_span("tid-1", name="db_query", duration_ms=10.0, success=True)
        trace = ctx.get_trace("tid-1")
        assert len(trace["spans"]) == 1
        assert trace["spans"][0]["name"] == "db_query"
        assert trace["spans"][0]["duration_ms"] == 10.0

    def test_add_span_to_missing_trace_is_noop(self):
        from app.tracing import TraceContext
        ctx = TraceContext()
        # Should not raise
        ctx.add_span("ghost", name="x", duration_ms=1.0, success=True)

    def test_multiple_spans_ordered(self):
        from app.tracing import TraceContext
        ctx = TraceContext()
        ctx.add_trace("tid-1", endpoint="/api/test")
        for name in ["route_enter", "db_query", "llm_call", "route_exit"]:
            ctx.add_span("tid-1", name=name, duration_ms=1.0, success=True)
        trace = ctx.get_trace("tid-1")
        names = [s["name"] for s in trace["spans"]]
        assert names == ["route_enter", "db_query", "llm_call", "route_exit"]


# ---------------------------------------------------------------------------
# T1.1b — ring buffer eviction
# ---------------------------------------------------------------------------

class TestTraceContextEviction:
    def test_eviction_at_capacity(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_traces=3)
        for i in range(4):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        # oldest (tid-0) should be gone
        assert ctx.get_trace("tid-0") is None
        assert ctx.get_trace("tid-3") is not None

    def test_size_never_exceeds_max(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_traces=5)
        for i in range(20):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        assert len(ctx.list_recent()) == 5

    def test_list_recent_newest_first(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_traces=3)
        for i in range(3):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        ids = [t["trace_id"] for t in ctx.list_recent()]
        assert ids[0] == "tid-2"  # most recent first

    def test_list_recent_limit_param(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_traces=10)
        for i in range(10):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        result = ctx.list_recent(limit=3)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# T1.1c — spans-per-trace cap
# ---------------------------------------------------------------------------

class TestSpanCap:
    def test_spans_capped_at_max(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_spans_per_trace=5)
        ctx.add_trace("tid-1", endpoint="/api/test")
        for i in range(10):
            ctx.add_span("tid-1", name=f"span-{i}", duration_ms=1.0, success=True)
        trace = ctx.get_trace("tid-1")
        assert len(trace["spans"]) == 5


# ---------------------------------------------------------------------------
# T1.1d — thread safety
# ---------------------------------------------------------------------------

class TestTraceContextThreadSafety:
    def test_concurrent_add_traces(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_traces=500)
        errors = []

        def writer(tid_prefix: str):
            try:
                for i in range(50):
                    ctx.add_trace(f"{tid_prefix}-{i}", endpoint="/api/test")
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=writer, args=(f"t{n}",)) for n in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # 10 threads × 50 = 500 traces, all within ring
        assert len(ctx.list_recent(limit=None)) == 500

    def test_concurrent_add_spans(self):
        from app.tracing import TraceContext
        ctx = TraceContext(max_spans_per_trace=500)
        ctx.add_trace("shared", endpoint="/api/test")
        errors = []

        def span_writer():
            try:
                for _ in range(50):
                    ctx.add_span("shared", name="span", duration_ms=1.0, success=True)
            except Exception as exc:
                errors.append(exc)

        threads = [threading.Thread(target=span_writer) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        trace = ctx.get_trace("shared")
        assert len(trace["spans"]) == 500


# ---------------------------------------------------------------------------
# T1.1e — disabled state
# ---------------------------------------------------------------------------

class TestTraceContextDisabled:
    def test_all_methods_noop_when_disabled(self):
        from app.tracing import TraceContext
        ctx = TraceContext(enabled=False)
        ctx.add_trace("tid-1", endpoint="/api/test")
        ctx.add_span("tid-1", name="x", duration_ms=1.0, success=True)
        assert ctx.get_trace("tid-1") is None
        assert ctx.list_recent() == []
