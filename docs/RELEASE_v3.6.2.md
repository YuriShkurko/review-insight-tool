# v3.6.2 - Agent Dashboard Demo Polish

Patch release on top of v3.6.1. This is still a v3.6.x reliability/demo-quality
release, not a v3.7.0 feature expansion.

## What Changed

- Added explicit agent-side dashboard ordering:
  - `get_workspace` lists current pinned widgets with exact IDs, titles, types,
    and positions.
  - `set_dashboard_order` validates a complete widget ID list and persists exact
    positions in one tool call.
  - The executor emits a `widgets_reordered` workspace event so the frontend
    blackboard updates immediately, then the normal reload reconciles state.
- Updated the agent system prompt so reverse/reorder/arrange/move requests use
  `set_dashboard_order` instead of approximating order through add/copy/remove
  side effects.
- Cleaned live-session chat residue:
  - successful pin/remove/copy/reorder actions render as compact confirmations.
  - failed pin attempts that later recover collapse into a muted
    "Recovered with a compatible chart type" note.
  - technical error details remain expandable instead of dominating the chat.
- Redesigned the desktop business detail layout so the dashboard is the primary
  full-screen canvas and chat appears as a floating assistant drawer.
- Kept mobile on the existing tabbed dashboard/chat pattern so small screens do
  not inherit the desktop overlay behavior.
- Polished dashboard cards and spacing for a more product-grade demo surface.

## Tests Added / Updated

- Backend integration:
  - reverse order request persists exactly.
  - duplicate widget followed by explicit reorder preserves copied data and final
    order.
- Frontend unit:
  - `widgets_reordered` SSE dispatch maps to the blackboard reducer.
  - recovered pin failures render as compact muted notes.
  - reorder success renders as a compact confirmation without raw JSON.

## Verification

```bash
pytest backend/tests/integration/test_agent_flow.py -q
# 28 passed, 1 warning

npx.cmd vitest run frontend/src/components/agent/__tests__/spinner.test.tsx frontend/src/lib/__tests__/workspaceBlackboard.test.ts
# Test Files  2 passed (2)
# Tests       30 passed (30)

cd frontend
npx.cmd tsc --noEmit
# no output; exit code 0
```

## Upgrade Notes

- No database migration required.
- No environment variable changes.
- Existing manual drag/drop reorder API remains unchanged.

## Known Limitations

- Desktop assistant drawer is collapsible but not yet user-resizable.
- Browser screenshot/manual visual QA was not run for this patch.
- Mobile uses the existing tab pattern; bottom-sheet assistant behavior remains a
  possible later polish item.
