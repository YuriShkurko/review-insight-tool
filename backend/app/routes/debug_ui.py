"""Debug UI snapshot endpoint.

Receives element selections from the frontend debug selector and stores them
in memory so the MCP debug server can read them via the `ui_snapshot` tool.

Routes are only meaningful when DEBUG_TRACE=true, but they are always
registered (returning empty/disabled responses when flag is off) so the
frontend does not get 404s when the flag is toggled at runtime.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.config import settings

router = APIRouter(prefix="/debug", tags=["debug"])

# Module-level snapshot store — single latest snapshot per server process.
# This is intentionally not persisted; it lives only as long as the process.
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
