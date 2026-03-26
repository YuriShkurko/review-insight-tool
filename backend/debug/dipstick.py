"""Dipstick — HTTP-backed query functions for the MCP debug tools.

All trace functions call the running backend via HTTP (localhost:8000/api/debug/*)
so they read from the *live* in-process ring buffer rather than a stale local copy.
This is the standard pattern: same as pprof, Prometheus, and ui_snapshot.

Exposed functions:
    get_trace_journey(trace_id)       → ordered span tree for one trace
    get_health_probe()                → component liveness map
    get_recent_traces(limit)          → newest-first trace summaries
    get_mutation_log(entity_id)       → mutation spans across all traces
    get_llm_call_log(business_id)     → LLM spans for a business
    get_ui_snapshot()                 → frontend element snapshot
    get_debug_selector_status()       → frontend debug selector config + current snapshot
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

_BACKEND_URL = "http://localhost:8000"
_TIMEOUT = 3.0


def _get(path: str, **params: Any) -> dict[str, Any]:
    """GET a debug endpoint on the running backend."""
    try:
        r = httpx.get(f"{_BACKEND_URL}{path}", params=params or None, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except Exception as exc:
        return {"error": str(exc), "tip": "Is the backend running with DEBUG_TRACE=true?"}


# ---------------------------------------------------------------------------
# 1. trace_journey
# ---------------------------------------------------------------------------


def get_trace_journey(trace_id: str) -> dict[str, Any]:
    """Return the ordered span tree for a single trace from the live backend."""
    return _get(f"/api/debug/traces/{trace_id}")


# ---------------------------------------------------------------------------
# 2. health_probe
# ---------------------------------------------------------------------------


def get_health_probe() -> dict[str, Any]:
    """Return a liveness map for DB, review provider, and trace buffer."""
    try:
        from sqlalchemy import create_engine, text

        from app.config import settings

        db_ok = False
        try:
            engine = create_engine(settings.DATABASE_URL)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass

        # Read trace buffer status from the live backend
        trace_info = _get("/api/debug/traces", limit=0)
        trace_enabled = trace_info.get("ok", False)

        return {
            "db": "ok" if db_ok else "error",
            "review_provider": settings.REVIEW_PROVIDER,
            "trace_buffer": "enabled" if trace_enabled else "disabled",
        }
    except Exception as exc:
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# 3. recent_traces
# ---------------------------------------------------------------------------


def get_recent_traces(limit: int = 20) -> dict[str, Any]:
    """Return the N most recent traces from the live backend ring buffer."""
    return _get("/api/debug/traces", limit=limit)


# ---------------------------------------------------------------------------
# 4. mutation_log
# ---------------------------------------------------------------------------


def get_mutation_log(entity_id: str) -> dict[str, Any]:
    """Return all write-flagged spans for a given entity_id from the live backend."""
    return _get(f"/api/debug/mutations/{entity_id}")


# ---------------------------------------------------------------------------
# 5. llm_call_log
# ---------------------------------------------------------------------------


def get_llm_call_log(business_id: str) -> dict[str, Any]:
    """Return all LLM-tagged spans for a given business_id from the live backend."""
    return _get(f"/api/debug/llm-calls/{business_id}")


# ---------------------------------------------------------------------------
# 6. ui_snapshot
# ---------------------------------------------------------------------------


def get_ui_snapshot() -> dict[str, Any]:
    """Fetch the latest frontend UI element snapshot from the backend."""
    return _get("/api/debug/ui-snapshot")


# ---------------------------------------------------------------------------
# 7. debug_selector_status
# ---------------------------------------------------------------------------

_FRONTEND_ENV = Path(__file__).resolve().parents[2] / "frontend" / ".env.local"


def get_debug_selector_status() -> dict[str, Any]:
    """Return the full debug selector configuration and current snapshot.

    Reads NEXT_PUBLIC_DEBUG_TRAIL from frontend/.env.local and fetches the
    latest ui-snapshot from the running backend.

    How the debug selector works:
      - Enabled when NEXT_PUBLIC_DEBUG_TRAIL=true (set in frontend/.env.local
        or via the NEXT_PUBLIC_DEBUG_TRAIL env var at Next.js dev-server start).
      - Hold CTRL in the browser → cursor changes to a crosshair (CSS:
        body[data-debug-selecting] * { cursor: crosshair }).
      - CTRL+click any element → purple glow outline (CSS animation
        _debug_shine on [data-debug-sel="primary"]) + dashed outline on
        all child elements ([data-debug-sel="child"]).
      - Each click appends to the selection and POSTs the snapshot to
        /api/debug/ui-snapshot on the backend.
      - Double-tap CTRL (≤300 ms) → deselect all and clear highlights.
      - The ◉ Debug panel (bottom-left) → Selector tab shows all selected
        elements with tag, React component name, CSS path, bounding rect.

    start with: make debug  (sets DEBUG_TRACE=true + NEXT_PUBLIC_DEBUG_TRAIL=true)
    """
    # Check frontend env file
    trail_enabled: bool | None = None
    env_file_found = _FRONTEND_ENV.exists()
    if env_file_found:
        try:
            text = _FRONTEND_ENV.read_text(encoding="utf-8")
            trail_enabled = "NEXT_PUBLIC_DEBUG_TRAIL=true" in text
        except Exception:
            trail_enabled = None

    # Fetch current snapshot from the live backend
    snapshot = _get("/api/debug/ui-snapshot")

    return {
        "selector_feature": {
            "ctrl_click": "Hold CTRL and click any element → purple glow highlight",
            "crosshair_cursor": "While CTRL is held, all cursors change to crosshair",
            "child_highlight": "All child elements get a dashed purple outline",
            "multi_select": "Each CTRL+click adds to the selection",
            "clear": "Double-tap CTRL (≤300ms) to deselect all",
            "panel": "◉ Debug button (bottom-left) → Selector tab",
            "css_primary": "[data-debug-sel='primary'] — animated purple glow",
            "css_child": "[data-debug-sel='child'] — dashed purple outline",
            "css_cursor": "body[data-debug-selecting] * { cursor: crosshair }",
        },
        "frontend_env": {
            "env_file": str(_FRONTEND_ENV),
            "env_file_found": env_file_found,
            "NEXT_PUBLIC_DEBUG_TRAIL": trail_enabled,
        },
        "start_command": "make debug",
        "snapshot": snapshot,
    }
