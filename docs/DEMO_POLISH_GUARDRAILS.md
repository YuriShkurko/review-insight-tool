# Demo Polish Guardrails

Phase 0 artifact for the DAMN demo polish roadmap. This file documents the
baseline checks to preserve while implementing later phases.

## Current Demo Baseline

The following behavior is considered already shipped and should not regress:

- `/businesses` loads authenticated businesses, offline demo mode notice,
  sandbox catalog, add/import actions, and delete actions.
- `/businesses/[id]` uses the dashboard-first dark shell on desktop.
- Executive summary renders from the loaded `Dashboard` payload and does not
  fabricate values when analysis is missing.
- Workspace renders sectioned dashboard groups from `dashboardSections.ts`.
- Clean Layout uses existing flat reorder persistence and preserves widget data.
- Drag/drop reorder, remove, manual pin, duplicate, incompatible recovery, and
  refresh persistence remain covered by deterministic agent/browser tests.
- Desktop assistant is secondary to the dashboard and can be collapsed/opened.
- Mobile uses dashboard/chat tabs rather than the desktop drawer.
- Agent `clear_dashboard` and `dashboard_cleared` workspace events clear the
  blackboard immediately.
- Tests must not require live LLM calls; use `ScriptedProvider`, mock review
  provider, direct REST helpers, or offline JSON data.

## Per-Phase Smoke Checklist

Run this checklist after each roadmap phase that touches UI, agent behavior, or
demo data.

### `/businesses` Launcher

- Authenticated user lands on `/businesses`.
- Existing business card/tile opens the correct workspace.
- Delete still asks for confirmation and removes only the selected business.
- Real-provider add form still accepts Maps URL/place ID.
- Offline provider hides the add form and shows the sandbox catalog path.
- Sandbox import adds a sample or changes an imported sample to an Open action.
- Empty state is useful and does not look like a broken page.
- Mobile width has no overlapping card text or clipped primary actions.

### Business Dashboard

- Header shows business name and fetch/analyze actions.
- Fetch Reviews and Analyze still disable while busy and surface errors.
- Executive summary renders with real dashboard data or honest placeholders.
- Workspace loading, empty, error-with-widgets, and error-without-widgets states
  are readable.
- Section headers render only for sections with widgets.
- Clean Layout groups by Overview, Trends, Issues, Evidence, Actions and
  persists after refresh.
- Drag/drop reorder works in normal mode.
- Remove widget works and refresh keeps it removed.
- Widget data is preserved after duplicate, reorder, Clean Layout, and refresh.

### Assistant

- Desktop drawer opens/collapses without covering required dashboard controls.
- Mobile chat tab opens and returns to dashboard tab cleanly.
- Suggested prompts send normal agent messages.
- Tool traces remain compact; details stay expandable.
- Recovered pin failures are muted after a successful compatible pin.
- Manual `+ Dashboard` pin from preview still adds a widget.
- Stream completion reloads/reconciles workspace state.

### Demo Data And Reliability

- Offline catalog still includes the intended demo scenarios.
- `sim_lager_ale_tlv` manifest entry points to existing generated JSON.
- Refreshing a business with existing reviews must not delete all reviews after
  a zero-result provider response.
- Synthetic monitor distinguishes failed checks from skipped/blocked checks.
- No new test path uses a real OpenAI/OpenRouter key.

## Validation Lanes

Use the smallest lane that covers the phase. Escalate to larger lanes for
shared state, agent contracts, or broad UI changes.

### Frontend Focused

```bash
cd frontend
npx.cmd tsc --noEmit
npx.cmd vitest run src/lib/__tests__/dashboardSections.test.ts src/lib/__tests__/workspaceBlackboard.test.ts src/components/agent/__tests__/spinner.test.tsx src/components/agent/widgets/__tests__/WidgetRenderer.test.tsx src/components/agent/widgets/__tests__/LineChart.test.ts
npx.cmd eslint src --ext .ts,.tsx
npx.cmd prettier --check "src/**/*.{ts,tsx}"
```

### Backend Focused

```bash
cd backend
python -m pytest tests/unit/test_agent_tools.py tests/integration/test_agent_flow.py -q
```

### Synthetic Monitor Focused

```bash
python -m pytest scripts/test_synthetic_monitor.py -q
```

### Browser E2E

Run when touching `/businesses`, dashboard layout, assistant behavior, workspace
events, or Playwright selectors.

```bash
# Terminal 1
make test-e2e-servers

# Terminal 2
make test-e2e-ui
```

The E2E lane requires a disposable PostgreSQL database reachable through
`E2E_DATABASE_URL` and must run with `LLM_PROVIDER=scripted`.

### Full Non-Browser CI Mirror

```bash
make validate
```

## Known Gaps To Track

- Full-repo Locus scan currently hits `backend/tmp_pytest_run` permission
  errors. Narrow scans on relevant subtrees are acceptable until that temp
  directory is removed or unlocked.
- Local Playwright cannot run unless the deterministic backend/frontend server
  harness is started and a local E2E database is reachable.
- Current Playwright helpers scope most dashboard assertions to desktop
  (`dashboard-desktop`). Add explicit mobile specs when a phase changes mobile
  layout meaningfully.
- Presentation Mode, command bar, narrative callouts, and redesigned
  `/businesses` launcher do not have coverage yet; each relevant phase must add
  focused tests.
- Avoid visual-only changes that make existing selectors ambiguous. Add stable
  `data-testid` values as part of the phase that introduces a new surface.
