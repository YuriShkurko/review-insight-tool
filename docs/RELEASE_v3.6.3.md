# v3.6.3 — Sectioned Canvas + Clean Layout + Monitor Reliability

## What shipped

### Dashboard: sectioned analytics canvas
The agent dashboard is now a **sectioned canvas** instead of a flat grid of cards.
Widgets are grouped visually into five sections — Overview, Trends, Issues, Evidence, Actions —
derived from `widget_type` (and title heuristics for `insight_list`/`summary_card`) on the frontend.
No new database column was introduced; grouping is a pure-render operation over the existing flat
`position` order.

### Executive summary strip
A compact KPI bar above the dashboard shows: total reviews, average rating, top issue, top praise,
and last-updated freshness. Data is sourced directly from the already-loaded `Dashboard` object.
All tiles show `—` gracefully when analysis hasn't run yet.

### Clean Layout button
A secondary **Clean Layout** button in the workspace header re-orders widgets by section (Overview
→ Trends → Issues → Evidence → Actions) by calling the existing `PATCH /agent/workspace/reorder`
endpoint — no new backend tool. Disabled when fewer than two widgets are pinned.
The agent also understands "clean layout", "auto-arrange", and "group by topic" and executes the
same section-order reorder via `set_dashboard_order`.

### Widget card polish
Drag handle and delete button are hover-only on `lg+` breakpoints (always visible on touch),
reducing visual noise on desktop. Cards gained a `data-widget-kind` attribute and a
`rounded-xl` / `border-border-subtle` surface consistent with the new section bands.

### Synthetic monitor: dependency-aware steps
- `analyze_competitor` timeout no longer fans out into `comparison_cold` and `comparison_cached`
  failures. Both steps are marked **skipped (blocked)** when a prerequisite didn't pass.
- A static `STEP_DEPENDENCIES` map encodes the dependency graph; `_check_deps` / `_skip`
  methods record skipped outcomes distinctly from failures in the final report.
- `analyze` and `analyze_competitor` get a 180s per-request timeout override; all other steps
  keep the 60s default.

### Synthetic monitor: Telegram env sanitisation
`TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` are `.strip()`-ed at module load time.
`_send_alert` validates the constructed URL for non-printable ASCII before sending;
a validation failure prints a clear stderr line and does not raise or suppress the monitor result.

## Key decisions

| Decision | Rationale |
|---|---|
| No `section` DB column | Pure-render grouping is visually identical for ≤20 widgets; migration blast radius not justified for demo polish |
| Reuse `set_dashboard_order` for Clean Layout | Smallest reliable tool already in place; no new endpoint needed |
| 180s timeout only for LLM analyze steps | Only `analyze` / `analyze_competitor` are synchronous LLM calls; bumping the global timeout would mask real hangs elsewhere |
| `.strip()` at import, not inside `_send_alert` | Env vars are set once; stripping at load time means all callers see clean values |
