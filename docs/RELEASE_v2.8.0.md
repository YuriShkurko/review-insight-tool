# v2.8.0 — Bug fixes, CI automation, and debug event trail

## What's New

### Business detail — stale-state and retry fixes
- **State cleared on error** — dashboard, reviews, competitors, and comparison are wiped before the error is set, so the previous business's data is never visible on the error screen
- **Retry spinner** — `setLoading(true)` fires at the start of every load attempt; "Retry loading" now shows a spinner instead of a flash of the success layout
- **Race condition guard** — `activeRouteIdRef` discards late API responses from a previous business ID after navigation, preventing stale data from overwriting the current page
- **Specific error messages** — 404 → "This business is no longer available…"; 422 → "Invalid business link…"; error screen now has a primary **Back to your businesses** button and a secondary **Retry loading** button

### GitHub Actions CI
- New `.github/workflows/ci.yml` — runs on every push and pull request to `main` / `master`
- **Backend job:** `ruff check`, `ruff format --check`, unit tests, integration tests (in-memory SQLite, no Postgres needed)
- **Frontend job:** `eslint`, `prettier --check`, `next build`
- CI validates only — no automatic deploys; Railway remains manual

### Makefile automation
- **`make validate`** — runs the same checks as CI (lint → unit tests → integration tests → frontend build); use this before pushing
- **`make ci-local`** — alias for `make validate`
- **`make frontend-build`** — `npm run build` in `frontend/` only
- **`make db-upgrade-local`** — `alembic upgrade head` with local Python and `backend/.env`
- **`make seed-offline-local`** — `python -m scripts.seed_offline` with local Python and `backend/.env`

### Debug event trail
- **Flag-controlled** — enabled only when `NEXT_PUBLIC_DEBUG_TRAIL=true` is set in `frontend/.env.local`; off by default, invisible to normal users
- **Ring buffer** — stores the last 200 events; older events are silently dropped, so memory stays bounded
- **Events captured:** route changes, auth (login / logout / restore), every `apiFetch` call (start / ok / fail), business detail load start / success / failure, fetch-reviews / analyze / compare / retry, business list add / delete, sandbox import / reset, competitor add / remove / prepare
- **Debug panel** — floating "◉ Debug" button in the bottom-left corner; opens an event list (most recent first) with kind badges, timestamps, and detail summaries; buttons: Copy JSON, Download `.json`, Clear
- **Safe by design** — sensitive keys (`token`, `password`, `authorization`, `secret`) are stripped; strings truncated at 200 chars

### Offline dataset cleanup
- Removed Abu Ali Supermarket (`abu_ali_reviews.json`) — unresolvable encoding corruption; will be re-added when data is clean
- Retail scenario is now **Rami Levy vs Lala Market** — 495 reviews, 8 businesses total

## Upgrade Notes

- No migrations needed
- Existing DB rows for `offline_abu_ali` businesses are harmless — the manifest no longer seeds new ones; users who imported it keep their data until they reset the sandbox
- Frontend: two new files (`debugTrail.ts`, `DebugPanel.tsx`) — safe to ignore unless `NEXT_PUBLIC_DEBUG_TRAIL=true`
- Integration test extended: `test_business_not_found_returns_404` now also asserts `GET /api/businesses/{id}/reviews` returns 404

## Breaking Changes

None.

## Full Changelog

v2.7.0...v2.8.0
