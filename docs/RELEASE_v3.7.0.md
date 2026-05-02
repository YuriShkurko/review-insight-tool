# v3.7.0 — AI analytics workspace, dashboard reset, monitor reliability

## What's New

### AI-assisted analytics workspace
- Executive summary band above the workspace surfaces reviews, average
  rating, top issue, top praise, freshness, and the current business
  snapshot.
- Workspace reworked into a sectioned analytics canvas with five sections:
  Overview, Trends, Issues, Evidence, Actions.
- Deterministic section classifier added in
  `frontend/src/lib/dashboardSections.ts` with unit coverage for
  classification, grouping, and flattening.
- Clean Layout presentation polish groups widgets by section and persists
  the order through the existing reorder path.
- Existing flat widget persistence model preserved; no database migration
  or section column was introduced.

### Premium dashboard and assistant polish
- Widget families redesigned so KPI, chart, evidence, recommendation, and
  narrative cards have distinct surfaces without changing widget contracts.
- Desktop layout reworked around a dashboard-first canvas with the
  assistant as a secondary drawer/panel.
- Mobile keeps the intentional dashboard/chat switching pattern instead of
  forcing desktop drawer parity.
- Subtle motion utilities added for workspace entry, panels, and
  presentation feedback.
- Assistant/chat styling, compact tool rows, suggestion prompts, and
  widget preview presentation all cleaned.

### Agent dashboard reset and rebuild behavior
- New `clear_dashboard` tool — atomic dashboard clearing for clear / wipe
  / reset / replace / rebuild / start-over intents.
- Executor emits `dashboard_cleared` workspace events after successful
  clear operations so the frontend blackboard updates immediately.
- Agent system prompt now requires a clear-first step on rebuild requests
  instead of piling new widgets on top of stale ones.
- Frontend blackboard handles `DASHBOARD_CLEARED` and clears stale
  workspace errors on clear / reorder / remove paths.
- Executor now runs data tools before `pin_widget` within a single
  assistant tool batch, so live models can return parallel-looking calls
  without breaking source-tool resolution.

### Synthetic monitor reliability
- Dependency-aware monitor steps: downstream comparison checks are
  reported as skipped when their prerequisite analysis fails.
- 180s per-step timeout overrides for the synchronous LLM-backed
  `analyze` and `analyze_competitor` checks; global default stays at 60s.
- Telegram env vars `.strip()`-ed at load time and alert URLs validated
  for non-printable characters before sending.

### Sim demo data restoration safeguards
- Deterministic `sim_lager_ale_tlv` offline data added with a 500-review
  narrative arc covering baseline, beer-festival surge, bad-keg incident,
  and recovery.
- `sim_lager_ale_tlv` manifest entry added so offline refreshes load the
  generated data.
- Provider-agnostic zero-result guard added in review refresh: if a
  provider returns no reviews for a business that already has reviews,
  existing rows are preserved instead of deleted.

### Browser coverage
- Playwright coverage added for Clean Layout grouping and refresh
  persistence.
- Existing dashboard / assistant test IDs preserved through the redesign
  so the prior deterministic agent E2E paths remain addressable.

### Tests
- Backend integration: dashboard clear emits `dashboard_cleared`;
  out-of-order tool batches still persist source-backed pinned widgets;
  agent dashboard ordering and pinning flows remain covered.
- Backend unit: `clear_dashboard` happy path and empty-dashboard
  behavior; agent tool contract includes the new clear operation.
- Frontend unit: dashboard section classifier, grouping, and flattening;
  blackboard handling for cleared widgets and preserved widget data;
  compact assistant/tool rendering and widget rendering paths.
- Playwright: Clean Layout groups mixed widgets into sections; order
  persists after refresh; widget data is not lost or duplicated by layout
  cleanup.
- Synthetic monitor: dependency-aware skipped steps; per-step blocked
  reporting; Telegram env sanitisation and invalid alert URL handling.

## Upgrade Notes

- No database migration required.
- No environment variable changes required.
- `clear_dashboard` is additive to the agent tool surface.
- Offline demo refreshes for `sim_lager_ale_tlv` now depend on the new
  manifest entry and generated review file.
- Run the full Playwright suite before tagging or pushing a release
  branch — the redesign turn skipped browser validation.

## Breaking Changes

None.

## Full Changelog

v3.6.3...v3.7.0
