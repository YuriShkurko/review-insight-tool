# v3.6.0 — Workspace Reload + Widget Data Integrity Fix

## What's New

### Backend — `pin_widget` refuses empty data (`backend/app/agent/executor.py`)
- Closes the regression where the agent could push an empty chart onto the dashboard.
- In `run_agent`, when `pin_widget` arrives with `data={}` AND no `source_tool` result is
  resolvable AND `tool_results` is empty, the executor now returns
  `{"pinned": false, "error": "..."}` directly. `_pin_widget` is not called, no
  `WorkspaceWidget` is committed, no `widget_added` SSE is emitted.
- Manual `+ Dashboard` pinning (`POST /api/businesses/{id}/agent/workspace`) is intentionally
  unchanged: the user initiates it, so an empty payload is treated as user intent.

### Frontend — diagnosable `apiFetch` (`frontend/src/lib/api.ts`)
- Every `trailEvent("api:start" | "api:fail" | "api:ok")` now includes the resolved
  `base_url`. Mobile/LAN failures are no longer opaque "Network error" with no clue —
  the debug trail shows the exact host the request went to.
- `apiStreamFetch` (SSE) is unchanged; only `apiFetch` was widened.

### Frontend — workspace banner surfaces failure category (`frontend/src/lib/workspaceBlackboard.tsx`)
- New `workspaceLoadErrorMessage(err)` helper prefixes the banner with a category:
  `Network:`, `Unauthorized:`, `Forbidden:`, `Not found:`, `Validation:`, `Server error:`.
- The reducer is unchanged — `LOAD_ERROR` already preserved widgets so a retry banner
  (not the full-page failed state) appears when widgets are still on screen.

### Mobile / LAN dev ergonomics
- `frontend/package.json`: new `dev:mobile` script (`next dev -H 0.0.0.0`).
- `Makefile`: new `make dev-mobile` target binding both backend and frontend to `0.0.0.0`.
- `README.md`: new "Mobile / LAN access" subsection in the local-dev block, plus a row
  in the Makefile commands table.
- The backend's CORS middleware already accepted private RFC1918 ranges
  (`10.x`, `192.168.x`, `172.16-31.x`) in dev — no change there.

### Tests added

**Backend integration tests** (`backend/tests/integration/test_agent_flow.py`)
- `test_agent_pin_widget_without_resolvable_data_is_refused` — `pin_widget` with empty
  data and no prior data tool returns `pinned: false`, emits no `workspace_event`, and
  leaves the workspace empty.
- `test_agent_duplicate_chart_pin_does_not_introduce_empty_widget` — first turn pins a
  real chart, second turn tries to pin again without re-fetching data; the second pin is
  refused and the workspace still contains only the original widget with real data.

**Frontend unit tests**
- `src/lib/__tests__/api.test.ts` — added `127.0.0.1` page-host case and a test confirming
  an explicit remote `NEXT_PUBLIC_API_URL` is not rewritten by `getApiBaseUrl()`.
- `src/lib/__tests__/workspaceBlackboard.test.ts` — `workspaceLoadErrorMessage` covers
  every category (`network` / `unauthorized` / `forbidden` / `not found` / `validation` /
  `server error`) plus the non-`ApiError` fallback.
- `src/components/agent/__tests__/workspace.test.tsx` — new file. Asserts `Workspace`
  renders the small banner (not the full failed state) when widgets are present and an
  error is set, and the full failed state when the workspace is empty.

## Verification

```bash
# Backend
cd backend
python -m ruff format --check .   # 98 files already formatted
python -m ruff check .             # All checks passed
python -m pytest tests/integration/test_agent_flow.py tests/unit/test_agent_tools.py
# 50 passed

# Frontend
cd frontend
npx tsc --noEmit                  # clean
npm run lint                       # clean
npm run format:check              # clean
npx vitest run                    # 10 files, 74 tests passed
```

## Upgrade Notes

- No database migrations needed.
- No environment variable changes.
- No infrastructure changes.
- The new `make dev-mobile` target is additive; `make dev`, `make backend`, `make frontend`
  behave identically to v3.5.x.

## Breaking Changes

None.

## Known Limitations

- `apiStreamFetch` does not emit trail events; SSE diagnostics on mobile would be a
  separate change.
- The failure-category banner is covered at the classifier-unit level, not via a
  Workspace integration test that triggers `LOAD_ERROR` end-to-end.
- LAN dev relies on the dev-only private-IP CORS regex; production still requires
  explicit `CORS_ORIGINS`.

## Full Changelog

v3.5.0...v3.6.0
