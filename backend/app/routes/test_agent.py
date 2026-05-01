"""Test-only routes for swapping agent scripts at runtime.

Mounted ONLY when settings.TESTING is true. Lets Playwright (or any
test driver) inject a per-scenario ScriptedProvider script before
hitting /api/businesses/{id}/agent/chat — so each E2E spec can drive
the same backend process through a different deterministic flow.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.llm.scripted import get_scripted_provider

router = APIRouter(prefix="/test", tags=["test"])


@router.post("/agent/script", status_code=204)
def set_agent_script(payload: dict) -> None:
    """Replace the active ScriptedProvider script.

    Body: {"script": [{"text": "...", "tool_calls": [...]}, ...]}
    Returns 204 on success, 422 if the body is malformed.
    """
    script = payload.get("script") if isinstance(payload, dict) else None
    if not isinstance(script, list):
        raise HTTPException(
            status_code=422,
            detail="Request body must be {'script': [...turns...]}.",
        )
    provider = get_scripted_provider()
    try:
        provider.set_script(script)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.post("/agent/script/reset", status_code=204)
def reset_agent_script() -> None:
    """Rewind the script cursor without clearing turns. Useful between scenarios."""
    get_scripted_provider().reset()
