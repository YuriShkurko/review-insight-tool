# v3.3.0 — Workspace charts, bootstrap API, pin reliability + SSL infra

## What's New

### Agent workspace charts (`backend/app/agent/tools.py`, `frontend/src/components/agent/widgets/`)
- New `get_rating_distribution` tool returns review counts by star rating (1–5)
  for a recent window with `bars` + `slices` payloads.
- New `BarChart` widget component renders the histogram on the dashboard
  canvas; `WidgetRenderer` routes `bar_chart` to it.
- `pin_widget` argument coercion strips unknown keys so models that emit extra
  JSON fields no longer break pinning. `_coerce_pin_widget_arguments` is the
  single source of truth.
- System prompt documents the tool→`widget_type` mapping so the LLM picks the
  correct chart for each data tool.
- `SummaryCard` renders pinned `get_top_issues` data via the `issues` array
  (no more empty card when issues are present).

### Bootstrap + offline business guard
- `GET /api/bootstrap` (no auth) returns `{"review_provider": "..."}` so the
  frontend can adapt to mock / offline / outscraper / simulation modes without
  a build-time flag.
- `POST /api/businesses` returns **403** when `REVIEW_PROVIDER=offline` —
  guides the user to `POST /api/sandbox/import` instead.
- `frontend/src/app/businesses/page.tsx` reads `/api/bootstrap` and hides the
  Google Maps URL form in offline mode.

### Workspace reload after every stream (`frontend/src/lib/useAgentChat.ts`)
- Previously the dashboard canvas only refreshed when `pin_widget` SSE had
  `pinned===true`, so missed pins or reordering left an empty Dashboard panel.
- Successful `done` events now trigger `loadWorkspace` unconditionally; dev
  console warns on workspace GET failure.

### Pin reliability + viewport + SSL (commit `5211bd1`)
- `ChatPanel` surfaces manual pin errors instead of silently swallowing them.
- `useAgentChat` calls `onAgentStreamDone` on error/catch paths, not just
  `done`, so the workspace reloads even when the stream errors after a
  successful pin.
- `ChatMessage` shows pin failure in red when `result.pinned !== true`.
- `system_prompt` replaces the run-on pin instruction with an explicit 3-step
  sequence (data tool → unchanged `pin_widget` args → report what was added;
  no invented widget types).
- `frontend/src/app/businesses/[id]/page.tsx` swaps `h-screen` for
  `h-[calc(100dvh-3rem)]` so content no longer scrolls under the NavBar.
- `infrastructure/04-alb.sh` adds optional `CERTIFICATE_ARN` support: HTTP-only
  by default; with cert, HTTP:80 redirects to HTTPS, HTTPS:443 routes
  `/api/*`. Idempotent upgrade path for existing HTTP-only stacks.
- `cd.yml` print step uses `vars.BACKEND_PUBLIC_URL` (https://) instead of a
  hardcoded `http://ALB_DNS`.
- `infrastructure/README.md` documents the SSL walkthrough.

### Synthetic monitor fix
- `scripts/synthetic_monitor.py` — `_pick_place_id` `NameError` resolved.

### Tests added

**Backend**
- `tests/unit/test_agent_tools.py` — `get_rating_distribution` shape,
  `pin_widget` argument coercion (4+ cases), prompt sequence regression
  (4 new prompt tests).
- `tests/integration/test_business_flow.py` — offline mode 403 on `POST
  /api/businesses`; `/api/bootstrap` shape.

**Frontend**
- `src/components/agent/__tests__/spinner.test.tsx` — 3 new `pin_widget`
  display tests for failure rendering and `Pinned to workspace` confirmation.

## Upgrade Notes

- No database migrations needed.
- `GET /api/bootstrap` is unauthenticated — safe to call from any client; no
  secrets are returned.
- AWS deployers: see `infrastructure/README.md` Step 2b for the optional ACM
  certificate flow. Existing HTTP-only stacks keep working until you provide
  `CERTIFICATE_ARN`.

## Breaking Changes

- `POST /api/businesses` now returns 403 in offline mode. Clients should call
  `GET /api/bootstrap` first (or handle the 403 gracefully).

## Full Changelog

v3.2.0...v3.3.0
