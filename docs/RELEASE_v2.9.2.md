# v2.9.2 — Debug env fix, selector status tool, and CI cleanup

## What's New

### `make debug` env propagation fix
- `frontend/.env.local` and `backend/.env` were both missing a trailing newline.
  Turbopack read `NEXT_PUBLIC_DEBUG_TRAIL` as `"true "` (trailing space) making
  `ENABLED = false` — the debug selector never mounted, CTRL+click did nothing.
  Pydantic rejected `DEBUG_TRACE="true "` with a `bool_parsing` validation error,
  crashing the backend before it could start.
- `Makefile` `debug` target: Windows `cmd` includes the space before `&&` in `set`
  values (`set VAR=true && next` → `VAR="true "`). Fixed to `set VAR=true&&` (no
  space). Frontend command now also uses `cmd /C` consistent with the backend.

### New `debug_selector_status` MCP tool
- `backend/debug/dipstick.py` adds `get_debug_selector_status()`: reads
  `frontend/.env.local` to report whether `NEXT_PUBLIC_DEBUG_TRAIL` is enabled,
  documents the full ctrl+click workflow (CSS classes, crosshair cursor, multi-select,
  double-tap clear, panel tab), and fetches the current snapshot in one call.
- Registered in `backend/debug/tools.py` as the `debug_selector_status` tool
  (tool inventory is now 14 tools). Use this before `ui_snapshot` to verify the
  selector is active.
- `backend/debug/mcp_server.py` instructions rewritten as a structured quick-reference
  covering the selector workflow, backend tracing, and the full tool inventory.

### Debug HTTP trace endpoints
- `backend/app/routes/debug_ui.py` now exposes the in-process ring buffer directly
  over HTTP (all `include_in_schema=False`):
  - `GET /api/debug/traces?limit=N` — recent trace summaries
  - `GET /api/debug/traces/{trace_id}` — full span tree for one trace
  - `GET /api/debug/mutations/{entity_id}` — write-flagged spans
  - `GET /api/debug/llm-calls/{business_id}` — LLM spans

### Competitor status indicator improvement
- Comparison prerequisites row in the business detail page now uses amber for
  partially-ready competitors (was incorrectly green), `→` arrow for not-yet-started
  (was `○`), and more descriptive status text: "rest will auto-analyze" /
  "Competitors will be auto-analyzed".

## CI fixes

### Backend (ruff)
- `SIM117`: merged nested `with` statements in `reviews.py`, `analysis_service.py`,
  and `test_trace_spans.py` into single parenthesised `with` blocks.
- `E402`: added `# noqa: E402` to the three Starlette imports that must follow
  `_load_dotenv_once()` in `tracing.py`.
- `RUF002/RUF003`: replaced EN dashes (`–`) and Unicode multiplication signs (`×`)
  with plain ASCII `-` and `x` across `tracing.py` and test files.
- `F401/I001`: auto-fixed unused imports and unsorted import blocks.

### Frontend (eslint)
- `react/no-unescaped-entities`: escaped literal `"` quotes in `DebugPanel.tsx`
  selector tab element text preview.

## Upgrade Notes

- No migrations needed.
- Delete `.next/` cache and restart `npm run dev` if you see the debug panel
  missing — stale Turbopack output may have `ENABLED=false` baked in.
- `make debug` now works correctly end-to-end on Windows; no manual env var
  patching required.

## Breaking Changes

None.

## Full Changelog

v2.9.1...v2.9.2
