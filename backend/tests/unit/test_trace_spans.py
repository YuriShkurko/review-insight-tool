"""T1.3 — Unit tests for trace_span() context manager and span emission.

Tests cover:
- trace_span() records a span in TraceContext with correct fields
- duration_ms is positive and plausible
- success=False on exception; exception re-raised
- Nested spans all land in the same trace
- metadata dict passed through to the span record
- No-op when TraceContext is disabled
"""

import time

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fresh_ctx(enabled: bool = True):
    from app.tracing import TraceContext
    return TraceContext(enabled=enabled)


# ---------------------------------------------------------------------------
# T1.3a — basic span recording
# ---------------------------------------------------------------------------

class TestTraceSpanBasic:
    def test_span_recorded_in_trace(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "db_query"):
            time.sleep(0.001)

        trace = ctx.get_trace("tid-1")
        assert len(trace["spans"]) == 1
        span = trace["spans"][0]
        assert span["name"] == "db_query"

    def test_span_duration_positive(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "db_query"):
            time.sleep(0.005)

        span = ctx.get_trace("tid-1")["spans"][0]
        assert span["duration_ms"] >= 1.0

    def test_span_success_true_on_clean_exit(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "route_enter"):
            pass

        assert ctx.get_trace("tid-1")["spans"][0]["success"] is True

    def test_span_success_false_on_exception(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with pytest.raises(RuntimeError):
            with trace_span(ctx, "tid-1", "llm_call"):
                raise RuntimeError("timeout")

        span = ctx.get_trace("tid-1")["spans"][0]
        assert span["success"] is False
        assert span["error"] == "RuntimeError"

    def test_span_exception_reraised(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with pytest.raises(ValueError, match="oops"):
            with trace_span(ctx, "tid-1", "x"):
                raise ValueError("oops")

    def test_span_metadata_stored(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "db_query", metadata={"table": "reviews", "rows": 42}):
            pass

        span = ctx.get_trace("tid-1")["spans"][0]
        assert span["metadata"]["table"] == "reviews"
        assert span["metadata"]["rows"] == 42


# ---------------------------------------------------------------------------
# T1.3b — nested spans
# ---------------------------------------------------------------------------

class TestTraceSpanNested:
    def test_nested_spans_all_in_same_trace(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "route_enter"):
            with trace_span(ctx, "tid-1", "db_query"):
                with trace_span(ctx, "tid-1", "llm_call"):
                    pass

        spans = ctx.get_trace("tid-1")["spans"]
        names = [s["name"] for s in spans]
        assert "route_enter" in names
        assert "db_query" in names
        assert "llm_call" in names

    def test_outer_span_duration_includes_inner(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx()
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "outer"):
            time.sleep(0.010)
            with trace_span(ctx, "tid-1", "inner"):
                time.sleep(0.005)

        spans = {s["name"]: s for s in ctx.get_trace("tid-1")["spans"]}
        assert spans["outer"]["duration_ms"] >= spans["inner"]["duration_ms"]


# ---------------------------------------------------------------------------
# T1.3c — disabled no-op
# ---------------------------------------------------------------------------

class TestTraceSpanDisabled:
    def test_noop_when_context_disabled(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx(enabled=False)
        ctx.add_trace("tid-1", endpoint="/api/test")

        with trace_span(ctx, "tid-1", "db_query"):
            pass

        # disabled ctx: get_trace always returns None
        assert ctx.get_trace("tid-1") is None

    def test_exception_still_reraised_when_disabled(self):
        from app.tracing import trace_span
        ctx = _fresh_ctx(enabled=False)

        with pytest.raises(KeyError):
            with trace_span(ctx, "tid-1", "x"):
                raise KeyError("still raised")
