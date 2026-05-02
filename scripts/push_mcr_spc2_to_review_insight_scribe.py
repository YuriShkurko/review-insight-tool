"""Copy plan artifact MCR-SPC-2 to Scribe MCP on localhost:8787 (workspace=review-insight).

The Cursor `user-scribe` MCP uses a different workspace; project `.mcp.json` points `scribe`
at http://localhost:8787/?workspace=review-insight. Run this after the local Scribe server
is listening on 8787.
"""
from __future__ import annotations

import json
import sys
import urllib.request

URL = "http://localhost:8787/mcp?workspace=review-insight"

GOAL = (
    "Tomorrow's implementation plan for fixing agent dashboard pinning reliability first, "
    "then chat viewport polish and AWS ALB SSL. Broader chart expansion, including pie charts, "
    "is deferred until pinning is verified."
)

PLAN = r"""# Fix Agent Dashboard And SSL

## Current Findings
- Dashboard pinning runs through [backend/app/agent/tools.py](backend/app/agent/tools.py), [backend/app/agent/executor.py](backend/app/agent/executor.py), [frontend/src/lib/useAgentChat.ts](frontend/src/lib/useAgentChat.ts), [frontend/src/components/agent/ChatPanel.tsx](frontend/src/components/agent/ChatPanel.tsx), and [frontend/src/app/businesses/[id]/page.tsx](frontend/src/app/businesses/[id]/page.tsx).
- Manual dashboard pin failures are currently easy to miss because [ChatPanel.tsx](frontend/src/components/agent/ChatPanel.tsx) catches errors silently.
- Agent-created pins can be lost or not reflected if the SSE stream ends without the exact success path the frontend expects.
- Pie charts are not implemented today. Existing chart widgets are `line_chart` and `bar_chart`; `trend_indicator` is a non-chart summary widget.
- The slight chat scroll is caused by `h-screen` in [frontend/src/app/businesses/[id]/page.tsx](frontend/src/app/businesses/[id]/page.tsx) while [frontend/src/app/providers.tsx](frontend/src/app/providers.tsx) renders a navbar above the page.
- AWS SSL is not wired yet. [infrastructure/04-alb.sh](infrastructure/04-alb.sh) creates only an HTTP listener; ACM + HTTPS listener + HTTP redirect need to be added.

## Implementation Plan
1. Make dashboard pinning observable and reliable.
   - Update manual `+ Dashboard` pin flow in [frontend/src/components/agent/ChatPanel.tsx](frontend/src/components/agent/ChatPanel.tsx) to show errors instead of swallowing them.
   - Refresh workspace after successful manual pins and after agent stream completion/error cleanup where a pin may have happened.
   - Surface `pin_widget` failure payloads in chat instead of rendering them like success.
   - Review backend mutation timing in [backend/app/agent/executor.py](backend/app/agent/executor.py) and [backend/app/agent/tools.py](backend/app/agent/tools.py) so a successful pin is committed before the UI is told it succeeded.

2. Tighten agent dashboard behavior.
   - Update [backend/app/agent/system_prompt.py](backend/app/agent/system_prompt.py) so dashboard-building requests explicitly follow: collect data tool result → call `pin_widget` with a supported `widget_type` → report what was added.
   - Keep widget payloads using the existing allowed types first, since the user chose reliability before broad chart expansion.
   - Add or adjust tests around `pin_widget` persistence and frontend refresh behavior.

3. Fix the chat viewport scroll.
   - Replace the business detail page root `h-screen` usage with a layout that fits below the navbar, likely `h-[calc(100dvh-3rem)]` or a shell-level `main` flex layout.
   - Apply the same height treatment to the loading state on that page.

4. Add AWS ALB SSL.
   - Extend [infrastructure/04-alb.sh](infrastructure/04-alb.sh) to accept or discover an ACM certificate ARN and create an HTTPS `443` listener.
   - Change the HTTP `80` listener to redirect to HTTPS once the certificate is available.
   - Update [infrastructure/README.md](infrastructure/README.md), [.github/workflows/cd.yml](.github/workflows/cd.yml), and any deployment variables/docs to use `https://` URLs.
   - Note: the ACM public certificate is free, but it requires a custom domain you control for DNS validation. The AWS ALB itself is still a paid resource.

5. Defer broader chart expansion until pinning is proven fixed.
   - After dashboard pinning is working, add `pie_chart` as a follow-up if desired by extending [backend/app/agent/tools.py](backend/app/agent/tools.py), [backend/app/agent/system_prompt.py](backend/app/agent/system_prompt.py), and [frontend/src/components/agent/WidgetRenderer.tsx](frontend/src/components/agent/WidgetRenderer.tsx).
   - The simplest first pie can reuse rating distribution data from `get_rating_distribution`.

## Verification
- Backend: run focused agent/workspace tests, especially `backend/tests/integration/test_agent_flow.py` and `backend/tests/unit/test_agent_tools.py`.
- Frontend: run focused unit tests for `useAgentChat` and widget rendering, then frontend lint/build.
- Manual smoke: from Chrome desktop and mobile viewport, ask the agent to add dashboard widgets, click manual `+ Dashboard`, refresh the page, and confirm widgets persist.
- Deployment: after ACM validation, deploy and verify `https://` loads frontend, `/api/bootstrap` works, and `http://` redirects to `https://`.
"""

DECISIONS = """- Priority order: fix reliable dashboard pinning first; do not start broad chart expansion until pinning is verified.
- SSL target: AWS ECS/ALB deployment, not Railway.
- SSL approach: use AWS ACM public certificate plus ALB HTTPS listener and HTTP-to-HTTPS redirect. ACM certificate is free, but requires a custom domain for DNS validation; ALB still has normal AWS cost.
- Chart scope: pie chart is a follow-up, not part of the first reliability fix. Existing supported chart widgets are `line_chart` and `bar_chart`; `trend_indicator` is not a chart.
- Likely first pie implementation later: reuse `get_rating_distribution` data for a `pie_chart` widget."""

TODOS = """- `pin-flow`: Fix dashboard pinning reliability and visible error handling across backend SSE/tool execution and frontend workspace refresh.
- `agent-prompt-tests`: Tighten agent dashboard instructions and add focused pinning tests.
- `chat-layout`: Fix business detail page height so chat fits below the navbar without slight scrolling.
- `aws-ssl`: Add ACM/HTTPS listener support and update AWS deployment docs/URLs.
- `chart-followup`: Document pie chart as a follow-up after pinning is verified, with the minimal files to extend."""

SOURCE_CONTEXT = """- README context: Review Insight Tool is a FastAPI + Next.js review intelligence app with provider abstraction, offline/demo modes, observability, and agent dashboard workspace.
- Existing Scribe context: `MCR-SPC-1` records the 2026-04-27 decisions around offline demo mode, bootstrap endpoint, agent pinning coercion, rating bar chart, and synthetic monitor place-id fix.
- Locus context: no dependency cycles or violations were found; scan focused mostly on frontend TypeScript with agent widgets and lib dependencies.
- Investigation notes: manual dashboard pin failures are currently easy to miss because frontend code swallows errors; agent-created pins can fail to appear if stream lifecycle/refresh does not line up; `h-screen` under the navbar causes the slight chat scroll; ALB is currently HTTP-only.
- **Migration:** First saved as `MCR-SPC-2` (scope `MicroSaas`) via Cursor `user-scribe` MCP; this artifact is the copy for workspace `review-insight` on port 8787 (project `scribe` MCP)."""

PROBLEM = """The agent dashboard builder is not reliably adding items to the persistent dashboard on desktop Chrome or mobile. Previous fixes did not resolve it. The agent also currently supports only basic trend/line/bar-style outputs despite earlier expectations around pie charts. The business detail/chat layout requires a slight scroll at 100% Chrome because the page uses full viewport height below a navbar. Production AWS ALB deployment is HTTP-only and needs SSL/HTTPS."""

DECISION = """Priority order is dashboard pinning reliability first, then chat viewport polish and AWS ALB SSL. Broader chart expansion, including pie charts, is deferred until pinning is proven fixed. SSL target is AWS ECS/ALB, using a free AWS ACM public certificate with DNS validation for a custom domain; ALB costs still apply. Existing chart widgets are `line_chart` and `bar_chart`; `trend_indicator` is not a chart. A later minimal pie implementation should likely reuse `get_rating_distribution` data for a new `pie_chart` widget."""

ACCEPTANCE = """- Manual `+ Dashboard` pin failures are visible to the user and do not fail silently.
- Agent `pin_widget` successes persist before the UI reports success, and workspace refreshes after manual pins and after agent stream completion/error cleanup.
- `pin_widget` failure payloads are surfaced in chat rather than shown as success.
- Dashboard-building prompt behavior explicitly follows data tool result -> `pin_widget` with supported `widget_type` -> report what was added.
- Business detail chat fits below the navbar without requiring a slight page scroll at 100% Chrome.
- AWS ALB has HTTPS listener using ACM certificate and HTTP redirects to HTTPS after certificate validation.
- Docs/deployment variables use `https://` where appropriate.
- Focused backend/frontend tests and manual desktop/mobile smoke checks pass."""


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
    status, headers, raw = _post(
        None,
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "push_mcr_spc2_to_review_insight", "version": "1"},
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
        "title": "Fix Agent Dashboard And SSL Plan — 2026-04-28",
        "goal": GOAL,
        "status": "draft",
        "priority": "high",
        "labels": [
            "cursor-plan",
            "agent-dashboard",
            "pinning",
            "aws-ssl",
            "planned-tomorrow",
            "from-user-scribe-mcr-spc-2",
        ],
        "sections": [
            {"name": "plan", "text": PLAN},
            {"name": "decisions", "text": DECISIONS},
            {"name": "todos", "text": TODOS},
            {"name": "source_context", "text": SOURCE_CONTEXT},
            {"name": "problem", "text": PROBLEM},
            {"name": "decision", "text": DECISION},
            {"name": "acceptance", "text": ACCEPTANCE},
        ],
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
