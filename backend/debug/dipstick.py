"""Dipstick — pure query functions for the 5 new MCP debug tools.

These are plain functions that take a TraceContext and return dicts.
They are imported by tools.py and wrapped into @mcp.tool() handlers there.
Keeping them as pure functions makes them trivially unit-testable.

Exposed functions:
    get_trace_journey(ctx, trace_id)      → ordered span tree for one trace
    get_health_probe()                    → component liveness map
    get_recent_traces(ctx, limit)         → newest-first trace summaries
    get_mutation_log(ctx, entity_id)      → mutation spans across all traces
    get_llm_call_log(ctx, business_id)    → LLM spans for a business
"""

from __future__ import annotations

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.tracing import TraceContext

_BACKEND_URL = "http://localhost:8000"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _db_ping() -> bool:
    """Try a SELECT 1 against the configured database. Returns True on success."""
    try:
        from sqlalchemy import create_engine, text
        from app.config import settings
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. trace_journey
# ---------------------------------------------------------------------------

def get_trace_journey(ctx: "TraceContext", trace_id: str) -> dict[str, Any]:
    """Return an ordered span list for a single trace_id."""
    trace = ctx.get_trace(trace_id)
    if trace is None:
        return {"error": f"trace_id {trace_id!r} not found in ring buffer"}
    return {
        "trace_id": trace["trace_id"],
        "endpoint": trace.get("endpoint", ""),
        "started_at": trace.get("started_at"),
        "spans": trace["spans"],
        "span_count": len(trace["spans"]),
    }


# ---------------------------------------------------------------------------
# 2. health_probe
# ---------------------------------------------------------------------------

def get_health_probe() -> dict[str, Any]:
    """Return a liveness map for DB, review provider, and trace buffer."""
    from app.config import settings
    from app.tracing import trace_context

    db_ok = _db_ping()

    return {
        "db": "ok" if db_ok else "error",
        "review_provider": settings.REVIEW_PROVIDER,
        "trace_buffer": "enabled" if trace_context._enabled else "disabled",
        "trace_buffer_size": len(trace_context._ring),
    }


# ---------------------------------------------------------------------------
# 3. recent_traces
# ---------------------------------------------------------------------------

def get_recent_traces(ctx: "TraceContext", limit: int = 20) -> dict[str, Any]:
    """Return the N most recent traces (newest first) as lightweight summaries."""
    traces = ctx.list_recent(limit=limit)
    summaries = [
        {
            "trace_id": t["trace_id"],
            "endpoint": t.get("endpoint", ""),
            "started_at": t.get("started_at"),
            "span_count": len(t["spans"]),
        }
        for t in traces
    ]
    return {"count": len(summaries), "traces": summaries}


# ---------------------------------------------------------------------------
# 4. mutation_log
# ---------------------------------------------------------------------------

def get_mutation_log(ctx: "TraceContext", entity_id: str) -> dict[str, Any]:
    """Return all spans flagged as mutations for a given entity_id."""
    all_traces = ctx.list_recent(limit=None)  # type: ignore[arg-type]
    mutations: list[dict[str, Any]] = []
    for trace in all_traces:
        for span in trace["spans"]:
            meta = span.get("metadata") or {}
            if meta.get("entity_id") == entity_id and meta.get("mutation"):
                mutations.append({
                    "trace_id": trace["trace_id"],
                    "name": span["name"],
                    "duration_ms": span["duration_ms"],
                    "success": span["success"],
                    "started_at": span.get("started_at"),
                    "metadata": meta,
                })
    return {"entity_id": entity_id, "mutation_count": len(mutations), "mutations": mutations}


# ---------------------------------------------------------------------------
# 5. llm_call_log
# ---------------------------------------------------------------------------

def get_ui_snapshot() -> dict[str, Any]:
    """Fetch the latest frontend UI element snapshot from the backend.

    The snapshot is posted by the browser-side debug selector whenever the
    user CTRL+clicks an element. Returns the selected element tree including
    tag, CSS path, React component name, bounding rect, text content, and
    the immediate children of each selected element.

    Requires:
        - Backend running on localhost:8000
        - DEBUG_TRACE=true on the backend
        - NEXT_PUBLIC_DEBUG_TRAIL=true on the frontend
    """
    try:
        import httpx
        r = httpx.get(f"{_BACKEND_URL}/api/debug/ui-snapshot", timeout=3.0)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc), "tip": "Is the backend running with DEBUG_TRACE=true?"}


def get_llm_call_log(ctx: "TraceContext", business_id: str) -> dict[str, Any]:
    """Return all LLM-tagged spans for a given business_id."""
    all_traces = ctx.list_recent(limit=None)  # type: ignore[arg-type]
    calls: list[dict[str, Any]] = []
    for trace in all_traces:
        for span in trace["spans"]:
            if span["name"] != "llm_call":
                continue
            meta = span.get("metadata") or {}
            if meta.get("business_id") != business_id:
                continue
            calls.append({
                "trace_id": trace["trace_id"],
                "name": span["name"],
                "duration_ms": span["duration_ms"],
                "success": span["success"],
                "started_at": span.get("started_at"),
                "metadata": meta,
            })
    return {"business_id": business_id, "call_count": len(calls), "llm_calls": calls}
