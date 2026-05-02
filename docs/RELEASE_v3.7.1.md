# v3.7.1 - Pre-push demo UI polish

Patch release on top of v3.7.0. Tightens the demo presentation surfaces
(launcher, dashboard scroll, trend chart) and fixes a comparison widget
rendering bug that left pinned period-over-period cards visually empty.

## What Changed

### Single dashboard scroll surface

- `ExecutiveSummary` is now rendered inside `Workspace`'s scroll container as
  a `scrollHeader` slot instead of as a sibling above it. Both desktop and
  mobile branches pass it through the same prop.
- Removes the dual-band layout where the dark executive band sat fixed above
  the only scrollable region; the page now has a single scroll surface with
  a sticky slim header.
- No widget contracts or persistence behavior changed.

### LineChart visual cleanup

- Replaced the 100x36 `preserveAspectRatio="none"` viewBox with a real
  320x100 viewBox using `xMidYMid meet`, eliminating cartoonish stretch.
- Smarter Y domain: `count` series anchor at zero with 15% headroom; rating
  series clamp to a padded sub-range of `[0, 5]` so small movements still
  read as movement.
- Replaced always-visible per-point dots with anchor endpoints plus a single
  highlighted dot for the selected index. Hover/click is driven by invisible
  hit zones so the line stays clean.
- Stroke is `1.5` with rounded caps and joins; light horizontal grid lines
  for readability.

### Launcher polish (icons, friendly names, sort)

- Added `frontend/src/lib/displayName.ts`: render-only helper that maps
  internal sandbox / sim place IDs (`sim_lager_ale_tlv`,
  `offline_lager_ale`, ...) to friendly demo names (e.g. "Craft Lager Bar
  (Demo)"). Keyword fallbacks cover lager, beer, sushi, burger, coffee,
  gym, market patterns, and a generic-name guard prevents `Business`
  placeholders from leaking through.
- Added `frontend/src/components/icons/BusinessTypeIcon.tsx`: inline SVG
  category icons for bar, restaurant, gym, cafe, and a generic fallback.
  No new dependency.
- Applied the helper + icon to `BusinessCard`, `SandboxCatalog`, the
  `/businesses` recommended chip, and the `[id]` dashboard header.
- Sorted the launcher grid by `updated_at` desc with the recommended sim
  business pinned first.
- Backend identifiers and routes are unchanged; this is render-only.

### Comparison widget renders pinned change-summary tool output

- `ComparisonWidget` (`comparison_card`) was reading only
  `comparison_summary` / `strengths` / `weaknesses` / `opportunities` and
  silently rendered an empty body when the agent pinned the output of
  `get_review_change_summary`, which uses `summary` / `current` /
  `previous` / `*_themes` / `rating_delta` / `count_delta` /
  `recommended_focus` / `limitation`.
- The widget now reads both shapes and renders period stat cards, deltas,
  current and previous top themes, and the recommended focus / limitation
  callout. Truly empty input now shows
  "No comparison data available." instead of an empty box.

### Validation harness fixes

- `frontend/vitest.config.ts` now excludes `e2e/**` so vitest no longer
  picks up Playwright specs (`Playwright Test did not expect test() to be
  called here`).
- `frontend/src/components/agent/__tests__/workspace.test.tsx` was
  updated to assert the stable `data-testid` for the failed state instead
  of an outdated `border-2 border-dashed border-red-300` class string that
  no longer exists in the redesigned banner.

## Tests Added / Updated

- Frontend unit:
  - `frontend/src/lib/__tests__/displayName.test.ts` covers override map,
    `- Sim` suffix stripping, generic `Business` placeholder guard,
    keyword fallbacks, titleizing, and pass-through of real-world names.
  - `frontend/src/components/agent/__tests__/workspace.test.tsx` updated
    to use stable testids for the failed state.
- Playwright (deterministic, mocked API):
  - `frontend/e2e/business-launcher.spec.ts` covers tile open and offline
    catalog import.
  - `frontend/e2e/dashboard-command-bar.spec.ts` covers command-bar agent
    prompt + pin and clean-layout / presentation actions.
  - `frontend/e2e/dashboard-presentation.spec.ts` covers Presentation Mode
    hide/restore.

## Verification

```bash
cd frontend
npx vitest run
# 13 files, 121 tests passed

npx tsc --noEmit
# passed

npm run lint
# passed

npx playwright test business-launcher dashboard-presentation dashboard-command-bar
# 5/5 passed
```

The remaining 8 Playwright failures in the wider suite (`agent-add-and-refresh`,
`agent-duplicate-widget`, `agent-incompatible-recovery`, `agent-manual-pin`,
`agent-remove-widget`, `dashboard-clean-layout`, `workspace-load-error`) all
fail in `seedUser` because the test backend is running with
`REVIEW_PROVIDER=offline`, which 403s `POST /businesses` with a Google Maps
link. Pre-existing env mismatch, unrelated to this release; tracked separately.

## Upgrade Notes

- No database migration required.
- No environment variable changes required.
- All changes are render-only or test-only; widget contracts, agent tool
  surface, and persistence are unchanged.

## Known Limitations

- The launcher friendly-name map is hand-curated. Adding a new sandbox
  scenario still requires an entry in `displayName.ts`.
- The keyword fallback heuristics are tuned for the current demo dataset
  and may need extension as new sim categories are introduced.

## Full Changelog

v3.7.0...v3.7.1
