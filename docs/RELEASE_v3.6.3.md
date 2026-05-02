# v3.6.3 — Sectioned canvas, Clean Layout, monitor reliability

## What's New

### Sectioned analytics canvas
- The agent dashboard is now a sectioned canvas instead of a flat grid of
  cards. Widgets are grouped visually into five sections — Overview,
  Trends, Issues, Evidence, Actions — derived from `widget_type` (with
  title heuristics for `insight_list` / `summary_card`).
- Grouping is a pure-render operation over the existing flat `position`
  order. No new database column was introduced.

### Executive summary strip
- Compact KPI bar above the dashboard surfaces total reviews, average
  rating, top issue, top praise, and last-updated freshness.
- Data is sourced directly from the already-loaded `Dashboard` object;
  tiles render `—` gracefully when analysis hasn't run yet.

### Clean Layout button
- Secondary **Clean Layout** button in the workspace header re-orders
  widgets by section (Overview → Trends → Issues → Evidence → Actions) by
  calling the existing `PATCH /agent/workspace/reorder` endpoint — no new
  backend tool. Disabled when fewer than two widgets are pinned.
- The agent also understands "clean layout", "auto-arrange", and "group by
  topic" and executes the same section-order reorder via
  `set_dashboard_order`.

### Widget card polish
- Drag handle and delete button are hover-only on `lg+` breakpoints
  (always visible on touch), reducing visual noise on desktop.
- Cards gained a `data-widget-kind` attribute and a `rounded-xl` /
  `border-border-subtle` surface consistent with the new section bands.

### Synthetic monitor: dependency-aware steps
- `analyze_competitor` timeout no longer fans out into `comparison_cold`
  and `comparison_cached` failures. Both steps are marked
  **skipped (blocked)** when a prerequisite didn't pass.
- A static `STEP_DEPENDENCIES` map encodes the dependency graph;
  `_check_deps` / `_skip` methods record skipped outcomes distinctly from
  failures in the final report.
- `analyze` and `analyze_competitor` get a 180s per-request timeout
  override; all other steps keep the 60s default.

### Synthetic monitor: Telegram env sanitisation
- `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are `.strip()`-ed at module
  load time.
- `_send_alert` validates the constructed URL for non-printable ASCII
  before sending; a validation failure prints a clear stderr line and does
  not raise or suppress the monitor result.

## Upgrade Notes

- No database migration required.
- No environment variable changes.
- Section grouping is frontend-derived; if manual section assignment is
  needed later, that should be a separate backend schema/tool change.

## Breaking Changes

None.

## Full Changelog

v3.6.2...v3.6.3
