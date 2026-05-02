# v3.7.1 — Pre-push demo UI polish

## What's New

### Single dashboard scroll surface
- `ExecutiveSummary` is now rendered inside `Workspace`'s scroll container
  through a new `scrollHeader` slot instead of as a sibling above it.
  Both desktop and mobile branches pass it through the same prop.
- Removes the dual-band layout where the dark executive band sat fixed
  above the only scrollable region; the page now has a single scroll
  surface with a sticky slim header.
- No widget contracts or persistence behavior changed.

### LineChart visual cleanup (`frontend/src/components/agent/widgets/LineChart.tsx`)
- Replaced the `100x36` `preserveAspectRatio="none"` viewBox with a real
  `320x100` viewBox using `xMidYMid meet`, eliminating the cartoonish
  stretch.
- Smarter Y domain: `count` series anchor at zero with 15% headroom;
  rating series clamp to a padded sub-range of `[0, 5]` so small
  movements still read as movement.
- Replaced always-visible per-point dots with anchor endpoints plus a
  single highlighted dot for the selected index. Hover/click is driven by
  invisible hit-zone rects so the line stays clean.
- Stroke is `1.5` with rounded caps and joins; light horizontal grid
  lines added for readability.

### Launcher polish (`/businesses`)
- New `frontend/src/lib/displayName.ts` — render-only helper that maps
  internal sandbox / sim place IDs (`sim_lager_ale_tlv`,
  `offline_lager_ale`, ...) to friendly demo names (e.g. "Craft Lager
  Bar (Demo)"). Keyword fallbacks cover lager, beer, sushi, burger,
  coffee, gym, market patterns, and a generic-name guard prevents
  `Business` placeholders from leaking through.
- New `frontend/src/components/icons/BusinessTypeIcon.tsx` — inline-SVG
  category icons for bar, restaurant, gym, cafe, and a generic fallback.
  No new dependency.
- Helper + icon applied to `BusinessCard`, `SandboxCatalog`, the
  `/businesses` recommended chip, and the `[id]` dashboard header.
- Launcher grid sorted by `updated_at` desc with the recommended sim
  business pinned first.
- Backend identifiers and routes are unchanged; this is render-only.

### Comparison widget renders pinned change-summary tool output
- `ComparisonWidget` (`comparison_card`) was reading only
  `comparison_summary` / `strengths` / `weaknesses` / `opportunities`
  and silently rendered an empty body when the agent pinned the output
  of `get_review_change_summary`, which uses `summary` / `current` /
  `previous` / `*_themes` / `rating_delta` / `count_delta` /
  `recommended_focus` / `limitation`.
- The widget now reads both shapes and renders period stat cards,
  deltas, current and previous top themes, and the recommended-focus /
  limitation callout.
- Truly empty input now shows "No comparison data available." instead
  of an empty box.

### Validation harness fixes
- `frontend/vitest.config.ts` now excludes `e2e/**` so vitest no longer
  picks up Playwright specs (`Playwright Test did not expect test() to
  be called here`).
- `frontend/src/components/agent/__tests__/workspace.test.tsx` updated
  to assert the stable `data-testid` for the failed state instead of an
  outdated `border-2 border-dashed border-red-300` class string that no
  longer exists in the redesigned banner.

### Tests
- Frontend unit: `displayName.test.ts` covers override map, `- Sim`
  suffix stripping, generic `Business` placeholder guard, keyword
  fallbacks, titleizing, and pass-through of real-world names.
- Playwright (deterministic, mocked API):
  `frontend/e2e/business-launcher.spec.ts` covers tile open and offline
  catalog import; `dashboard-command-bar.spec.ts` covers command-bar
  agent prompt + pin and clean-layout / presentation actions;
  `dashboard-presentation.spec.ts` covers Presentation Mode hide and
  restore.

## Upgrade Notes

- No database migration required.
- No environment variable changes required.
- All changes are render-only or test-only; widget contracts, agent tool
  surface, and persistence are unchanged.
- The launcher friendly-name map is hand-curated. Adding a new sandbox
  scenario still requires an entry in `displayName.ts`.

## Breaking Changes

None.

## Full Changelog

v3.7.0...v3.7.1
