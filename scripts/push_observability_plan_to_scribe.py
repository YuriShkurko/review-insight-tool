"""One-shot: create Scribe artifact from docs/OBSERVABILITY_PLAN.md via MCP HTTP (localhost:8787)."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "OBSERVABILITY_PLAN.md"
URL = "http://localhost:8787/mcp?workspace=review-insight"


def _post(session_id: str | None, body: dict) -> tuple[int, dict[str, str], str]:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        URL,
        data=data,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **({"Mcp-Session-Id": session_id} if session_id else {}),
        },
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
        headers = {k.lower(): v for k, v in resp.headers.items()}
        return resp.status, headers, raw


def _parse_sse_json(raw: str) -> dict | None:
    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            try:
                return json.loads(line[5:].strip())
            except json.JSONDecodeError:
                continue
    return None


def main() -> int:
    if not PLAN.is_file():
        print("Missing", PLAN, file=sys.stderr)
        return 1
    text = PLAN.read_text(encoding="utf-8")

    status, headers, raw = _post(
        None,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "push_observability_plan", "version": "1"},
            },
        },
    )
    if status != 200:
        print("initialize HTTP", status, raw[:500], file=sys.stderr)
        return 1
    sid = headers.get("mcp-session-id")
    if not sid:
        print("No mcp-session-id header", headers, file=sys.stderr)
        return 1

    _post(sid, {"jsonrpc": "2.0", "method": "notifications/initialized"})

    arguments = {
        "action": "create",
        "kind": "spec",
        "scope": "review-insight",
        "title": "Observability system plan",
        "status": "draft",
        "labels": ["observability", "otel", "grafana", "from-repo"],
        "sections": [
            {
                "name": "body",
                "text": text,
            }
        ],
        "links": {"docs": [str(PLAN.relative_to(ROOT)).replace("\\", "/")]},
    }

    status2, _, raw2 = _post(
        sid,
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {"name": "artifact", "arguments": arguments},
        },
    )
    msg = _parse_sse_json(raw2)
    if status2 != 200:
        print("tools/call HTTP", status2, raw2[:800], file=sys.stderr)
        return 1
    if msg and msg.get("error"):
        print("MCP error:", json.dumps(msg["error"], indent=2), file=sys.stderr)
        return 1
    print(json.dumps(msg, indent=2) if msg else raw2[:2000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
