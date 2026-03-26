"""Debug endpoints — UI snapshot + trace data.

All routes are always registered. When DEBUG_TRACE=false they return a
disabled response so the frontend/MCP server never gets a 404.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/debug", tags=["debug"])

# Module-level snapshot store — single latest snapshot per server process.
_snapshot: dict[str, Any] | None = None


@router.post("/ui-snapshot", include_in_schema=False)
def receive_ui_snapshot(payload: dict) -> dict:
    """Accept an element snapshot POSTed by the frontend debug selector."""
    global _snapshot
    if not settings.DEBUG_TRACE:
        return {"ok": False, "reason": "DEBUG_TRACE not enabled"}
    _snapshot = payload
    return {"ok": True, "element_count": len(payload.get("selected", []))}


@router.get("/ui-snapshot", include_in_schema=False)
def get_ui_snapshot() -> dict:
    """Return the latest element snapshot for MCP or other tooling."""
    if not settings.DEBUG_TRACE:
        return {"ok": False, "reason": "DEBUG_TRACE not enabled", "selected": []}
    if _snapshot is None:
        return {"ok": True, "selected": [], "note": "No snapshot received yet"}
    return {"ok": True, **_snapshot}


# ── Trace data endpoints (read from the live in-process ring buffer) ──────────


@router.get("/traces", include_in_schema=False)
def get_recent_traces(limit: int = 20) -> dict:
    """Return the N most recent traces from the in-process ring buffer."""
    if not settings.DEBUG_TRACE:
        return {"ok": False, "reason": "DEBUG_TRACE not enabled", "count": 0, "traces": []}
    from app.tracing import trace_context

    traces = trace_context.list_recent(limit=limit)
    summaries = [
        {
            "trace_id": t["trace_id"],
            "endpoint": t.get("endpoint", ""),
            "started_at": t.get("started_at"),
            "span_count": len(t["spans"]),
        }
        for t in traces
    ]
    return {"ok": True, "count": len(summaries), "traces": summaries}


@router.get("/traces/{trace_id}", include_in_schema=False)
def get_trace(trace_id: str) -> dict:
    """Return the full span tree for a single trace."""
    if not settings.DEBUG_TRACE:
        return {"ok": False, "reason": "DEBUG_TRACE not enabled"}
    from app.tracing import trace_context

    trace = trace_context.get_trace(trace_id)
    if trace is None:
        return {"ok": False, "error": f"trace_id {trace_id!r} not found"}
    return {
        "ok": True,
        "trace_id": trace["trace_id"],
        "endpoint": trace.get("endpoint", ""),
        "started_at": trace.get("started_at"),
        "spans": trace["spans"],
        "span_count": len(trace["spans"]),
    }


@router.get("/mutations/{entity_id}", include_in_schema=False)
def get_mutations(entity_id: str) -> dict:
    """Return all write-flagged spans for a given entity_id."""
    if not settings.DEBUG_TRACE:
        return {"ok": False, "reason": "DEBUG_TRACE not enabled", "mutations": []}
    from app.tracing import trace_context

    all_traces = trace_context.list_recent(limit=None)  # type: ignore[arg-type]
    mutations = []
    for trace in all_traces:
        for span in trace["spans"]:
            meta = span.get("metadata") or {}
            if meta.get("entity_id") == entity_id and meta.get("mutation"):
                mutations.append(
                    {
                        "trace_id": trace["trace_id"],
                        "name": span["name"],
                        "duration_ms": span["duration_ms"],
                        "success": span["success"],
                        "started_at": span.get("started_at"),
                        "metadata": meta,
                    }
                )
    return {
        "ok": True,
        "entity_id": entity_id,
        "mutation_count": len(mutations),
        "mutations": mutations,
    }


@router.get("/llm-calls/{business_id}", include_in_schema=False)
def get_llm_calls(business_id: str) -> dict:
    """Return all LLM call spans for a given business_id."""
    if not settings.DEBUG_TRACE:
        return {"ok": False, "reason": "DEBUG_TRACE not enabled", "llm_calls": []}
    from app.tracing import trace_context

    all_traces = trace_context.list_recent(limit=None)  # type: ignore[arg-type]
    calls = []
    for trace in all_traces:
        for span in trace["spans"]:
            if span["name"] != "llm_call":
                continue
            meta = span.get("metadata") or {}
            if meta.get("business_id") != business_id:
                continue
            calls.append(
                {
                    "trace_id": trace["trace_id"],
                    "name": span["name"],
                    "duration_ms": span["duration_ms"],
                    "success": span["success"],
                    "started_at": span.get("started_at"),
                    "metadata": meta,
                }
            )
    return {"ok": True, "business_id": business_id, "call_count": len(calls), "llm_calls": calls}
