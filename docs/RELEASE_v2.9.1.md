# v2.9.1 — Trace dipstick debugging and Hebrew offline data repair

## What's New

### End-to-end request tracing (`DEBUG_TRACE`)
- New `backend/app/tracing.py` adds an in-memory trace context with ring-buffered traces/spans, deterministic sampling, and TTL cleanup.
- `TraceMiddleware` is mounted in `backend/app/main.py` when `DEBUG_TRACE=true`, injecting and echoing `X-Trace-Id` per request.
- Added trace spans in key flows:
  - `backend/app/routes/reviews.py` (fetch + analyze route spans)
  - `backend/app/services/analysis_service.py` (LLM call span path)
- Frontend API trail now captures `X-Trace-Id` from responses in `frontend/src/lib/api.ts`.

### MCP dipstick tools expansion
- New `backend/debug/dipstick.py` provides focused debug helpers for:
  - trace journey inspection
  - health probing
  - recent traces
  - mutation log
  - LLM call log
  - UI snapshot fetch
- `backend/debug/tools.py` now exposes these tools in the existing `review-insight-debug` MCP server and documents the expanded tool inventory.

### UI selector bridge for frontend-to-MCP introspection
- New `frontend/src/lib/debugSelector.ts`:
  - `CTRL+click` to select elements (multi-select)
  - double-tap `CTRL` to clear selection
  - serializes tag/path/component/text/bounds/data attributes
- New backend endpoint `backend/app/routes/debug_ui.py`:
  - `POST /api/debug/ui-snapshot`
  - `GET /api/debug/ui-snapshot`
- Route is registered in `backend/app/routes/__init__.py`; endpoints are useful when `DEBUG_TRACE=true`.
- `frontend/src/components/DebugPanel.tsx` and `frontend/src/app/providers.tsx` were updated to surface selection state in the debug UI.

### Testing and tuning
- Added backend unit tests for tracing and dipstick behaviors under `backend/tests/unit/`.
- Added frontend Vitest setup and debug trail tests:
  - `frontend/vitest.config.ts`
  - `frontend/src/lib/__tests__/debugTrail.test.ts`
  - dependency updates in `frontend/package.json` and `frontend/package-lock.json`
- Added `backend/debug/TRACE_TUNING.md` with tuning/benchmark guidance.

### Offline Hebrew dataset repair
- Regenerated corrupted Hebrew fields in offline data files:
  - `backend/data/offline/shupersal_reviews.json`
  - `backend/data/offline/rami_levy_reviews.json`
  - `backend/data/offline/lala_market_reviews.json`
  - `backend/data/offline/beer_garden_reviews.json`
- Added display and provider hardening:
  - `frontend/src/components/ReviewList.tsx` uses `dir="auto"` and text repair fallback for legacy rows.
  - `backend/app/providers/offline_provider.py` applies safe best-effort mojibake repair when loading offline reviews.

## Upgrade Notes

- No migrations needed.
- New tracing features are opt-in and off by default:
  - backend tracing: `DEBUG_TRACE=true`
  - MCP debugger: `DEBUG_MCP=true`
  - frontend debug UI: `NEXT_PUBLIC_DEBUG_TRAIL=true`
- After offline data repair, run sandbox reset + re-import so stored rows refresh from corrected source files.

## Breaking Changes

None.

## Full Changelog

v2.9.0...v2.9.1
