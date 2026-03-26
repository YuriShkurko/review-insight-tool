# Trace Tuning Guide

Configuration reference for the E2E request tracing system (`app/tracing.py`).
All settings are env vars read at server startup. Safe to leave unset — defaults are production-friendly.

---

## Environment Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `DEBUG_TRACE` | bool (`true`/unset) | off | Master switch. Must be `true` to enable any tracing. |
| `DEBUG_TRACE_MAX_TRACES` | int | `500` | Ring buffer capacity. Oldest trace evicted when full. |
| `DEBUG_TRACE_MAX_SPANS` | int | `50` | Max spans per trace. Oldest span evicted when full. |
| `DEBUG_TRACE_SAMPLE_RATE` | float | `1.0` | Fraction of requests traced (0.0 = none, 1.0 = all). Hash-deterministic per trace ID. |
| `DEBUG_TRACE_TTL_HOURS` | int | `24` | Traces older than this are evicted by `cleanup()`. Set to `0` to disable TTL. |

---

## Memory Footprint

At default settings (500 traces × 50 spans) with ~200-byte metadata per span:

| Config | Est. RSS |
|---|---|
| Default (500 × 50) | ~8 MB |
| Large (1000 × 100) | ~30 MB |
| Hard ceiling tested | < 50 MB |

Rule of thumb: each span costs ~300–500 bytes of Python object overhead including deque node, dict, and string interning.

---

## Sampling

`DEBUG_TRACE_SAMPLE_RATE` uses the first 8 hex digits of `SHA-256(trace_id)` mapped to `[0, 1)`. This means:

- **Deterministic**: the same `trace_id` always produces the same sample/no-sample decision, across restarts and processes.
- **Uniform**: UUID-based trace IDs distribute evenly, so a rate of `0.1` stores ~10% of traffic.
- **Co-sampled**: if a trace is sampled, all its spans are stored (no partial traces).

```bash
# Store 10% of requests (high-traffic staging)
DEBUG_TRACE_SAMPLE_RATE=0.1

# Store everything (local dev default)
DEBUG_TRACE_SAMPLE_RATE=1.0
```

---

## TTL Cleanup

`TraceContext.cleanup()` scans the ring and evicts traces with `started_at < now - ttl_hours * 3600`. It holds the lock only during the compaction step and is safe to call from a background thread.

To run cleanup on a schedule, call it from a lifespan background task or a cron job:

```python
import asyncio
from app.tracing import trace_context

async def _cleanup_loop():
    while True:
        await asyncio.sleep(60)
        evicted = trace_context.cleanup()
        if evicted:
            logger.debug("trace_cleanup evicted=%d", evicted)
```

Setting `DEBUG_TRACE_TTL_HOURS=0` disables TTL entirely — the ring grows until capacity and then evicts by recency only.

---

## Benchmark Results (2026-03-26)

Measured on Windows 10, Python 3.13, in-process TestClient, 200 requests to `GET /api/businesses`:

| Mode | p99 latency |
|---|---|
| Trace OFF | 4.75 ms |
| Trace ON (default settings) | 4.39 ms |
| **Delta** | **-0.36 ms** |

The tracing overhead at default settings is **sub-millisecond** and unmeasurable against request variance. The 5ms p99 budget from the campaign spec is satisfied with large margin.

---

## When to Tune

| Symptom | Action |
|---|---|
| MCP `trace_journey` shows old data | Reduce `DEBUG_TRACE_TTL_HOURS` or call `cleanup()` more often |
| Ring fills up too fast (evicting recent traces) | Increase `DEBUG_TRACE_MAX_TRACES` |
| Span detail missing | Increase `DEBUG_TRACE_MAX_SPANS` |
| High memory on traffic spikes | Reduce `DEBUG_TRACE_SAMPLE_RATE` to 0.1–0.5 |
| Tracing overhead visible in profiler | File an issue — expected overhead is <1ms p99 |
