# v3.4.0 — Workspace blackboard, widget state parity, chart interactions

## What's New

### Workspace blackboard provider (`frontend/src/lib/workspaceBlackboard.tsx`)
- New `WorkspaceBlackboardProvider` reducer replaces the prop-drilled
  refetch-callback pattern. Single source of truth for dashboard widget
  state with `INIT_LOAD` / `LOADED` / `LOAD_ERROR` / `WIDGET_ADDED` /
  `WIDGET_REMOVED` / `WIDGET_REORDERED` actions.
- Backend `pin_widget` returns the authoritative widget payload after commit
  and the executor emits a `workspace_event` SSE; the frontend applies
  `WIDGET_ADDED` immediately, deduplicates by id, and still reloads on stream
  completion as a reconciliation pass.
- Empty or unsupported widget data renders explicit fallbacks instead of
  blank cards.
- `frontend/src/app/businesses/[id]/page.tsx` re-architected to consume the
  blackboard for both the desktop and mobile Workspace mounts (175 lines
  changed) — no more parallel `loadWorkspace` callbacks.

### Expanded chart widget set (`frontend/src/components/agent/widgets/`)
- `DonutChart` — full pie/donut SVG renderer with slice labels and legend.
- `ComparisonChart` — side-by-side comparison renderer for
  `get_review_change_summary` results.
- `HorizontalBarChart` — used by `get_top_issues` to render top issues
  ranked by count.
- `ToolCallIndicator` updated to humanise the new tool names with proper
  loading/checkmark states.

### Improved agent review analysis tools (`backend/app/agent/tools.py`)
- New `get_review_insights(focus, period, limit)` — returns synthesised
  themes (positive/negative/balanced), examples, limitations, and a
  recommended action; respects `this_week` / `this_month` / `last_month` /
  `past_30d` etc. instead of dumping raw reviews.
- New `get_review_change_summary(current_period, previous_period)` —
  compares two windows for "what changed" questions; returns rating/count
  deltas, per-period themes, examples, and a recommended action.
- `get_top_issues` rewrite: complaint-theme grouping when an `Analysis` row
  exists; star-bucket fallback otherwise. Severity tiers
  (critical/notable/minor), recency multiplier, representative quote
  selection, and a `bars` array for direct charting.
- System prompt rewritten (74 lines) to route open-ended quality questions
  to `get_review_insights` / `get_review_change_summary` instead of
  `query_reviews`.

### Widget state parity, drag persistence, chart tap (commit `e064716`)
- `pin_widget` now requires `source_tool` (enum of `DATA_TOOL_NAMES`).
  Executor maintains a `tool_results` registry keyed by tool name and
  resolves the exact result at pin time — eliminates the "No data to show"
  failure when the LLM dropped the `data` payload.
- `WIDGET_REORDERED` reducer reassigns `position` fields after reorder so
  `sort-by-position` no longer reverts the dropped order on the next render.
- `LineChart`, `BarChart`, `DonutChart` — click/tap selects a data point and
  shows a detail panel (label + value + percentage) below the chart. Works
  on mobile without relying on SVG hover-only tooltips.

### Tests added

**Backend**
- `tests/unit/test_agent_tools.py` — `get_review_insights` (focus/period/empty
  variants), `get_review_change_summary` (deltas, sparse-data limitations),
  expanded `get_top_issues` (severity/recency/quote/limit), `pin_widget`
  `source_tool` stripping, `DATA_TOOL_NAMES` ↔ `TOOL_WIDGET_TYPES` sync
  (~159 new test lines).
- `tests/integration/test_agent_flow.py` — blackboard pin round trip with
  `widget_added` SSE; unsupported widget type rejection.

**Frontend**
- `src/lib/__tests__/workspaceBlackboard.test.ts` — reducer actions,
  `dispatchWorkspaceEvent`, agent-vs-manual widget shape parity,
  `WIDGET_REORDERED` position-field reassignment.
- `src/components/agent/widgets/__tests__/WidgetRenderer.test.tsx` — donut /
  bar / line / comparison routing + chart titles.
- `src/components/agent/__tests__/widgetFallbacks.test.tsx` — empty-data
  fallback assertions for unsupported widget types.

## Upgrade Notes

- No database migrations needed.
- No environment variable changes.
- Models calling `pin_widget` must now pass `source_tool` — the parameter is
  enforced in the OpenAI tool schema. Existing prompts already include the
  3-step sequence so most models comply without changes.

## Breaking Changes

- Tool callers must include `source_tool` in `pin_widget` calls. Calls
  without it are rejected at the schema level.

## Full Changelog

v3.3.0...v3.4.0
