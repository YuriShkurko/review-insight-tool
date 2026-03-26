"""T4.7-T4.9 - Tests for tuning: sampling, TTL eviction, and memory ceiling.

All tests are written before the implementation (RED phase).

T4.7 — Sampling determinism
    - Same trace_id always sampled/not-sampled at same rate
    - At sample_rate=0.0 no traces stored
    - At sample_rate=1.0 all traces stored
    - At sample_rate=0.5 approximately half stored (within 15% margin)

T4.8 — TTL eviction
    - Traces older than TTL are purged by cleanup()
    - Recent traces within TTL survive the cleanup
    - cleanup() is a no-op when TTL is None (disabled)

T4.9 — Memory ceiling
    - A full ring (max_traces x max_spans) uses reasonable memory
"""

from __future__ import annotations

import sys

# ---------------------------------------------------------------------------
# T4.7 — Sampling determinism
# ---------------------------------------------------------------------------

class TestSampling:
    def test_sample_rate_zero_stores_nothing(self):
        from app.tracing import TraceContext
        ctx = TraceContext(sample_rate=0.0)
        for i in range(100):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        assert len(ctx.list_recent(limit=None)) == 0

    def test_sample_rate_one_stores_everything(self):
        from app.tracing import TraceContext
        ctx = TraceContext(sample_rate=1.0, max_traces=200)
        for i in range(100):
            ctx.add_trace(f"tid-{i}", endpoint="/api/test")
        assert len(ctx.list_recent(limit=None)) == 100

    def test_sampling_is_deterministic_for_same_trace_id(self):
        """Same trace_id must always produce the same sampling decision."""
        from app.tracing import TraceContext
        ctx1 = TraceContext(sample_rate=0.5, max_traces=1000)
        ctx2 = TraceContext(sample_rate=0.5, max_traces=1000)
        ids = [f"stable-id-{i:04d}" for i in range(200)]
        for tid in ids:
            ctx1.add_trace(tid, endpoint="/api/test")
        for tid in ids:
            ctx2.add_trace(tid, endpoint="/api/test")
        stored1 = {t["trace_id"] for t in ctx1.list_recent(limit=None)}
        stored2 = {t["trace_id"] for t in ctx2.list_recent(limit=None)}
        assert stored1 == stored2

    def test_sampling_approximately_correct_rate(self):
        """At 50% rate, within 15% of 1000 traces should be stored (350-650)."""
        import uuid as _uuid

        from app.tracing import TraceContext
        ctx = TraceContext(sample_rate=0.5, max_traces=1000)
        for _ in range(1000):
            ctx.add_trace(str(_uuid.uuid4()), endpoint="/api/test")
        stored = len(ctx.list_recent(limit=None))
        assert 350 <= stored <= 650, f"Expected ~500, got {stored}"

    def test_spans_not_stored_for_unsampled_trace(self):
        """add_span on an unsampled trace_id is a complete no-op."""
        from app.tracing import TraceContext
        ctx = TraceContext(sample_rate=0.0)
        ctx.add_trace("unsampled", endpoint="/api/test")
        ctx.add_span("unsampled", name="db_query", duration_ms=5.0, success=True)
        assert ctx.get_trace("unsampled") is None


# ---------------------------------------------------------------------------
# T4.8 — TTL eviction
# ---------------------------------------------------------------------------

class TestTTLEviction:
    def test_old_trace_evicted_after_cleanup(self):
        from app.tracing import TraceContext
        ctx = TraceContext(ttl_hours=1)
        ctx.add_trace("old", endpoint="/api/test")
        # Manually backdate the trace's started_at by 2 hours
        with ctx._lock:
            ctx._index["old"]["started_at"] -= 7200  # 2 h in seconds
        ctx.cleanup()
        assert ctx.get_trace("old") is None

    def test_recent_trace_survives_cleanup(self):
        from app.tracing import TraceContext
        ctx = TraceContext(ttl_hours=1)
        ctx.add_trace("fresh", endpoint="/api/test")
        ctx.cleanup()
        assert ctx.get_trace("fresh") is not None

    def test_cleanup_noop_when_ttl_none(self):
        from app.tracing import TraceContext
        ctx = TraceContext(ttl_hours=None)
        ctx.add_trace("ageless", endpoint="/api/test")
        with ctx._lock:
            ctx._index["ageless"]["started_at"] -= 999999  # ancient
        ctx.cleanup()
        assert ctx.get_trace("ageless") is not None

    def test_cleanup_preserves_ring_integrity(self):
        """After cleanup the ring and index remain consistent."""
        from app.tracing import TraceContext
        ctx = TraceContext(ttl_hours=1, max_traces=10)
        for i in range(5):
            ctx.add_trace(f"old-{i}", endpoint="/api/test")
            with ctx._lock:
                ctx._index[f"old-{i}"]["started_at"] -= 7200
        for i in range(5):
            ctx.add_trace(f"fresh-{i}", endpoint="/api/test")
        ctx.cleanup()
        recent = ctx.list_recent(limit=None)
        ids = {t["trace_id"] for t in recent}
        assert all(tid.startswith("fresh-") for tid in ids)
        assert len(ids) == 5
        # Ring and index must be in sync
        with ctx._lock:
            assert len(ctx._ring) == len(ctx._index)

    def test_multiple_cleanups_idempotent(self):
        from app.tracing import TraceContext
        ctx = TraceContext(ttl_hours=1, max_traces=10)
        ctx.add_trace("fresh", endpoint="/api/test")
        ctx.cleanup()
        ctx.cleanup()
        ctx.cleanup()
        assert ctx.get_trace("fresh") is not None


# ---------------------------------------------------------------------------
# T4.9 — Memory ceiling
# ---------------------------------------------------------------------------

class TestMemoryCeiling:
    def test_full_ring_under_50mb(self):
        """A fully saturated ring must not exceed 50 MB of Python object overhead."""
        from app.tracing import TraceContext

        ctx = TraceContext(max_traces=500, max_spans_per_trace=50)
        long_meta = {"key": "x" * 200}  # 200-char strings per span

        for i in range(500):
            ctx.add_trace(f"tid-{i:04d}", endpoint="/api/businesses/test/analyze")
            for j in range(50):
                ctx.add_span(
                    f"tid-{i:04d}",
                    name=f"span-{j}",
                    duration_ms=float(j),
                    success=True,
                    metadata=long_meta,
                )

        size = sys.getsizeof(ctx._ring)
        for trace in ctx._ring:
            size += sys.getsizeof(trace)
            size += sys.getsizeof(trace["spans"])
            for span in trace["spans"]:
                size += sys.getsizeof(span)

        fifty_mb = 50 * 1024 * 1024
        assert size < fifty_mb, f"Ring buffer used {size / 1024 / 1024:.1f} MB, expected < 50 MB"
