# v3.6.2 — Agent dashboard ordering, chat residue cleanup, desktop canvas redesign

## What's New

### Explicit agent-side dashboard ordering
- New `get_workspace` tool — lists current pinned widgets with exact IDs,
  titles, types, and positions so the agent can reason about layout without
  re-fetching state through side channels.
- New `set_dashboard_order` tool — validates a complete widget-ID list and
  persists exact positions in one call. Reverse, reorder, arrange, and move
  requests now route through this instead of approximating order via
  add/copy/remove side effects.
- Executor emits a `widgets_reordered` workspace event so the frontend
  blackboard updates immediately, then the normal reload reconciles state.
- Agent system prompt updated to require `set_dashboard_order` for any
  ordering intent.

### Live-session chat residue cleanup
- Successful pin / remove / copy / reorder actions render as compact
  confirmations instead of raw tool JSON.
- Failed pin attempts that later recover collapse into a muted
  "Recovered with a compatible chart type" note.
- Technical error details remain expandable but no longer dominate the chat.

### Desktop business detail layout
- Desktop now treats the dashboard as a primary full-screen canvas with
  the assistant as a floating drawer, instead of forcing a side-by-side
  split.
- Mobile keeps the existing tabbed dashboard/chat pattern; small screens do
  not inherit the desktop overlay behaviour.
- Dashboard cards and spacing polished for a more product-grade demo
  surface.

### Tests
- Backend integration: reverse-order request persists exactly; duplicate
  widget followed by explicit reorder preserves copied data and final order.
- Frontend unit: `widgets_reordered` SSE dispatch maps to the blackboard
  reducer; recovered pin failures render as compact muted notes; reorder
  success renders as a compact confirmation without raw JSON.

## Upgrade Notes

- No database migration required.
- No environment variable changes.
- Existing manual drag/drop reorder API remains unchanged; the new tools
  are additive on the agent side.

## Breaking Changes

None.

## Full Changelog

v3.6.1...v3.6.2
