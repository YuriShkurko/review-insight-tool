# v4.0.0 — Business Insight, agent hardening, workspace theming, README revamp

Major release. The product positioning, agent surface, dashboard widgets, and documentation
catch up to the **Business Insight** multi-signal copilot direction that had been landing in
smaller patches. This version bumps **4.0.0** because the change set is large end-to-end:
new backend tools and widget types, feature-flag wiring for the agent pipeline, deterministic
routing fixes for money-flow charts, expanded automated tests, a full **README** rewrite, and a
coordinated **dark-mode / semantic-surface** pass across the launcher, offline catalog, assistant,
and analytics canvas.

## What's New

### Business Insight modules (reviews + demo signals)

- **Business health** — `get_business_health` and `health_score` widget with sub-scores,
  drivers, risks, and provenance fields (`is_demo`, confidence, limitations).
- **Signal timeline** — `get_signal_timeline` and `signal_timeline` widget for dated narrative
  signals from review-derived data.
- **Demo business signals** (deterministic, gated) — `get_sales_summary`, `get_operations_summary`,
  `get_local_presence_summary`, `get_social_signal_summary` with matching widgets; configurable via
  `BUSINESS_INSIGHT_ENABLED`, `DEMO_SIGNALS_ENABLED`, and `SIGNAL_PROVIDER` in `backend/app/config.py`.
- **Opportunities and action plan** — `get_opportunities` / `opportunity_list` and
  `get_action_plan` / `action_plan` with evidence-backed structure.
- **Money flow** — `get_financial_flow` and `money_flow` widget; chart pipeline uses shared
  `frontend/src/lib/chartColors.ts` where appropriate for consistent palettes.

### Agent pipeline and prompts

- **Active tool definitions** — executor uses `get_active_tool_definitions()` so BI and demo-signal
  tools respect runtime flags instead of a static tool list only.
- **System prompt** — conditional BI/demo routing, widget selection, and **comprehensive / improvement**
  dashboard fill steps that explicitly include health, timeline, sales (when enabled), money flow,
  and action plan alongside review analytics.
- **Command bar** — “Build business dashboard” and “Clear and rebuild” prompts name concrete
  tool→widget pairs so quick actions bias toward a full Business Insight canvas, not review-only
  widgets.
- **Money-flow bypass hardening** — `_create_custom_chart_data` rejects profit-bridge-shaped custom
  bar payloads with a structured `money_flow_redirect`; executor adds a second-line
  `pin_rejects_money_flow_bar_masquerade` check so `create_custom_chart_data` + horizontal bar
  cannot silently stand in for `get_financial_flow` + `money_flow`.

### Frontend workspace and charts

- **WidgetRenderer** extended for new widget types; **SortableWidgetCard** and related chart
  widgets updated for layout, contrast, and dark-mode-friendly rendering paths.
- **Dashboard sections** — classifier and tests updated for new `widget_type` values and grouping.
- **Workspace canvas** — replaces hardcoded `bg-[#f6f7fb]` / paper-white shells with semantic
  `bg-surface`, `bg-surface-card`, and `border-border` so **dark mode** matches the rest of the app;
  presentation mode header and section bands use the same token family.

### Dark mode and launcher readability

- **`/businesses`** — semantic surfaces for the page shell, **BusinessCard**, and **SandboxCatalog**
  (compact and expanded offline catalog: chips, scenario panels, stat boxes, reset control).
- **Assistant** — **ChatPanel**, **ChatMessage**, **ToolCallIndicator**, **SuggestedPrompts**, and
  inline error surfaces use semantic text and background tokens for readable contrast in `.dark`.
- **Business detail layout** — desktop dashboard column, floating assistant shell, and mobile tab
  chrome aligned with semantic tokens.

### Documentation and ops copy

- **README** — large revamp (separate authoring pass): Business Insight framing, table of contents,
  architecture overview, agent design, module matrix, configuration, testing, deployment, and
  roadmap alignment with the current stack.
- **Supporting docs** — `backend/README.md`, `docs/STAGING.md`, and `docs/ROADMAP_DEMO_POLISH.md`
  touched for naming and consistency.

### Testing

- **Backend** — expanded `tests/unit/test_agent_tools.py` (BI tools, money-flow intercept, pin
  masquerade, system prompt fragments) and **integration** coverage in `test_agent_flow.py` for
  scripted agent flows where applicable.
- **Frontend** — **WidgetRenderer** fixture coverage for new widgets; **SandboxCatalog** token
  hygiene tests; **spinner** / **ChatMessage** tests updated for semantic classnames and failure
  styling; **dashboardSections** tests extended.

## Key decisions

| Decision | Rationale |
|----------|-----------|
| Ship as **v4.0.0** (not 3.8.x) | User-facing product identity, README, multi-tool agent surface, and widget contracts move together; semver major signals the bundle. |
| Feature flags for BI / demo signals | Keeps production defaults aligned with current demo while allowing a narrower tool surface without code removal. |
| Deterministic money-flow intercept | LLM-only guidance was insufficient; backend rejects profit-bridge-shaped `create_custom_chart_data` and refuses ambiguous pins. |
| Semantic tokens vs hex for workspace | `bg-[#f6f7fb]` does not participate in `.dark`; `bg-surface` keeps one source of truth in `globals.css`. |
| README revamp in-repo | Single entry point for onboarding, architecture, and demo status; maintained alongside code. |

## Upgrade Notes

- Confirm env vars for **BI** and **demo signals** match the intended environment (`BUSINESS_INSIGHT_ENABLED`, `DEMO_SIGNALS_ENABLED`, `SIGNAL_PROVIDER`).
- After deploy, run your usual **`make validate`** (or CI equivalent) and smoke the **offline catalog**, **workspace**, and **assistant** in both light and dark themes.
- Refresh marketing or in-app **screenshots** if you rely on them; UI chrome and README narrative changed materially.

## Breaking Changes

None for HTTP routes, database schema, or JWT contract: existing API paths and persistence models are unchanged.

**Semantic versioning:** this is **4.0.0** because the *product and agent surface* expanded materially (new tools/widgets, README narrative, theming). Operators who pinned documentation or runbooks to “Review Insight only” should re-read the README **Demo Status** and **Business Insight Modules** sections.

## Known Limitations

- **Playwright:** full browser E2E for every new BI tool→widget path may still be environment-dependent; run the suite you rely on before tagging if CI did not already prove it on this branch.
- **Widget internals:** chart SVGs and some widget bodies may still carry chart-specific colors; the dark-mode pass focused on **shell chrome**, launcher, catalog, assistant, and workspace canvas tokens.
- **Release tag range:** the **Full Changelog** line below assumes the previous shipping tag is **`v3.7.1`**. If your last tag differs, substitute it when publishing (or use `origin/main~N..HEAD` until tags exist locally).

## Verification

- `make validate` — or equivalent: backend ruff + pytest, frontend lint + typecheck + unit tests, production build.
- Optional: full **Playwright** suite if configured for Business Insight scripted flows.
- Manual: dark mode on `/businesses`, expanded catalog, workspace with widgets, assistant thread
  (user message, assistant reply, tool row, preview, input).

## Full Changelog

v3.7.1...v4.0.0

