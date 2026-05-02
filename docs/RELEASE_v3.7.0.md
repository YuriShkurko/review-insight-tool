# v3.7.0 - AI Analytics Workspace, Dashboard Reset, Monitor Reliability

Feature release on top of the agent-dashboard reliability work. This release
turns the dashboard into a more complete AI-assisted analytics workspace while
adding safer dashboard reset/rebuild behavior, better browser coverage, and
guardrails for the synthetic demo dataset.

## What Changed

### AI-assisted analytics workspace

- Added an executive summary band above the workspace with reviews, average
  rating, top issue, top praise, freshness, and the current business snapshot.
- Reworked the workspace into a sectioned analytics canvas:
  - Overview
  - Trends
  - Issues
  - Evidence
  - Actions
- Added deterministic section classification in
  `frontend/src/lib/dashboardSections.ts` and tests for classifier, grouping,
  and flattening behavior.
- Added Clean Layout presentation polish that groups widgets by section and
  persists the order through the existing reorder path.
- Preserved the existing flat widget persistence model; no database migration
  or section column was introduced.

### Premium dashboard and assistant polish

- Redesigned widget families so KPI, chart, evidence, recommendation, and
  narrative cards have distinct surfaces without changing widget contracts.
- Improved the desktop layout around a dashboard-first canvas with the
  assistant as a secondary drawer/panel.
- Kept mobile on an intentional dashboard/chat switching pattern instead of
  forcing desktop drawer parity.
- Added subtle motion utilities for workspace entry, panels, and presentation
  feedback.
- Cleaned assistant/chat styling, compact tool rows, suggestion prompts, and
  widget preview presentation.

### Agent dashboard reset and rebuild behavior

- Added a `clear_dashboard` tool for atomic dashboard clearing when the user
  asks to clear, wipe, reset, replace, rebuild, or start over.
- Executor now emits `dashboard_cleared` workspace events after successful clear
  operations so the frontend blackboard updates immediately.
- System prompt now tells the agent to clear the dashboard first for rebuild
  requests instead of piling new widgets on top of stale ones.
- Frontend blackboard handles `DASHBOARD_CLEARED` and clears stale workspace
  errors on clear/reorder/remove paths.
- Executor now runs data tools before `pin_widget` within a single assistant
  tool batch, so live models can return parallel-looking calls without breaking
  source-tool resolution.
- Backend unit and integration tests cover `clear_dashboard`, workspace event
  emission, prompt guidance, and out-of-order tool batches.

### Synthetic monitor reliability

- Added dependency-aware monitor steps so downstream comparison checks are
  reported as skipped when their prerequisite analysis fails.
- Added 180s per-step timeout overrides for the synchronous LLM-backed
  `analyze` and `analyze_competitor` checks while keeping the global default
  at 60s.
- Stripped Telegram env vars at load time and validated alert URLs for
  non-printable characters before sending.
- Added monitor tests for dependency skipping, blocked-step reporting,
  Telegram env cleanup, and alert URL validation.

### Sim demo data restoration safeguards

- Added deterministic `sim_lager_ale_tlv` offline data with a 500-review
  narrative arc covering baseline, beer festival surge, bad-keg incident, and
  recovery.
- Added the `sim_lager_ale_tlv` manifest entry so offline refreshes can load
  the generated data.
- Added a provider-agnostic zero-result guard in review refresh: if a provider
  returns no reviews for a business that already has reviews, existing rows are
  preserved instead of deleted.

### Browser coverage

- Added Playwright coverage for Clean Layout grouping and refresh persistence.
- Existing dashboard/assistant test IDs were preserved through the redesign so
  the prior deterministic agent E2E paths remain addressable.

## Tests Added / Updated

- Backend integration:
  - dashboard clear emits `dashboard_cleared`.
  - out-of-order tool batches still persist source-backed pinned widgets.
  - agent dashboard ordering and pinning flows remain covered.
- Backend unit:
  - `clear_dashboard` happy path and empty-dashboard behavior.
  - agent tool contract includes the new clear operation.
- Frontend unit:
  - dashboard section classifier, grouping, and flattening.
  - blackboard handling for cleared widgets and preserved widget data.
  - compact assistant/tool rendering and widget rendering paths.
- Playwright:
  - Clean Layout groups mixed widgets into sections.
  - order persists after refresh.
  - widget data is not lost or duplicated by layout cleanup.
- Synthetic monitor:
  - dependency-aware skipped steps.
  - per-step blocked reporting.
  - Telegram env sanitisation and invalid alert URL handling.

## Verification

```bash
npx.cmd tsc --noEmit
# passed

npx.cmd vitest run src/lib/__tests__/dashboardSections.test.ts src/lib/__tests__/workspaceBlackboard.test.ts src/components/agent/__tests__/spinner.test.tsx src/components/agent/widgets/__tests__/WidgetRenderer.test.tsx src/components/agent/widgets/__tests__/LineChart.test.ts
# 5 files, 76 tests passed

npx.cmd prettier --check "src/**/*.{ts,tsx}"
# All matched files use Prettier code style!

npx.cmd eslint src --ext .ts,.tsx
# passed

npm.cmd run build
# Next build compiled successfully
```

Additional validation reported in the Scribe decision history:

- `scripts/test_synthetic_monitor.py` passed.
- Dashboard section tests passed.
- Existing focused agent/workspace tests were updated for clear/rebuild flows.

## Upgrade Notes

- No database migration required.
- No environment variable changes required.
- `clear_dashboard` is additive to the agent tool surface.
- Offline demo refreshes for `sim_lager_ale_tlv` now depend on the new manifest
  entry and generated review file.

## Known Limitations

- Playwright E2E was not run during the final redesign implementation turn
  because the app/server harness was not running then. Run the browser suite
  before tagging or pushing a release branch.
- Mobile has visual/interaction coverage through the responsive implementation,
  but the new Clean Layout Playwright spec targets the desktop dashboard scope.
- The section model is still frontend-derived. If users need to manually assign
  widgets to sections later, that should be a separate backend schema/tool
  change.

## Full Changelog

v3.6.3...v3.7.0
