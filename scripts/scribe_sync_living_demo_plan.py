"""Sync docs/LIVING_DEMO_WORLD_PLAN.md to Scribe artifact RVW-SPC-3 (replace body section)."""
from __future__ import annotations

import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "LIVING_DEMO_WORLD_PLAN.md"
ARTIFACT_ID = "RVW-SPC-3"
URL = "http://localhost:8787/mcp?workspace=review-insight"


def post(session_id: str | None, body: dict) -> tuple[str | None, str]:
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if session_id:
        headers["Mcp-Session-Id"] = session_id
    req = urllib.request.Request(
        URL,
        data=json.dumps(body).encode("utf-8"),
        method="POST",
        headers=headers,
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.headers.get("mcp-session-id"), resp.read().decode("utf-8", errors="replace")


def parse_sse(raw: str) -> dict | None:
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
    return None


def call_artifact(session_id: str, arguments: dict) -> dict | None:
    _, raw = post(
        session_id,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "artifact", "arguments": arguments},
        },
    )
    msg = parse_sse(raw)
    if msg and msg.get("error"):
        print(json.dumps(msg["error"], indent=2), file=sys.stderr)
        return None
    return msg


def main() -> int:
    if not PLAN.is_file():
        print("Missing", PLAN, file=sys.stderr)
        return 1
    text = PLAN.read_text(encoding="utf-8")

    sid, _ = post(
        None,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "scribe_sync_living_demo", "version": "1"},
            },
        },
    )
    if not sid:
        print("No session", file=sys.stderr)
        return 1
    post(sid, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    # Replace primary markdown section
    call_artifact(
        sid,
        {
            "action": "detach_section",
            "id": ARTIFACT_ID,
            "name": "body",
        },
    )
    msg = call_artifact(
        sid,
        {
            "action": "attach_section",
            "id": ARTIFACT_ID,
            "name": "body",
            "text": text,
        },
    )
    if not msg:
        return 1
    out = msg.get("result", {}).get("content", [{}])[0].get("text", str(msg))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
