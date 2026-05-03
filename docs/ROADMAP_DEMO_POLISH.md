# DAMN Demo Polish Roadmap

Planning artifact only. Do not implement from this document without opening a
focused implementation phase first.

## Current Baseline

Business Insight already has the core agentic dashboard foundation:

- sectioned analytics canvas on the business detail page
- executive summary band
- Clean Layout grouping and persistence
- desktop floating/collapsible assistant drawer
- mobile dashboard/chat tabs
- `clear_dashboard` and rebuild-capable agent behavior
- deterministic agent E2E and CI-oriented Playwright infrastructure
- synthetic monitor dependency handling and stable offline demo data safeguards

The remaining gap is demo impact. The dashboard is now much stronger than the
business launcher, and the product needs a cohesive path from "choose a demo
workspace" to "present a sharp AI-generated customer insight story."

## Context Gathered

- `frontend/src/app/businesses/page.tsx` is still a narrow list page with a
  basic heading, plain add/import controls, simple offline-mode panel, simple
  `BusinessCard` rows, and a utilitarian `SandboxCatalog`.
- `frontend/src/app/businesses/[id]/page.tsx` already has the dark product
  shell, executive summary, dashboard-first desktop layout, assistant drawer,
  and mobile tabs.
- `frontend/src/components/agent/Workspace.tsx` already handles section
  grouping, Clean Layout, optimistic reorder, error banners, and empty states.
- `frontend/src/lib/dashboardSections.ts` is a pure frontend classifier. The
  roadmap should preserve this until user-editable sections are truly needed.
- `frontend/src/components/agent/ChatPanel.tsx`, `ChatMessage.tsx`,
  `ToolCallIndicator.tsx`, and `SuggestedPrompts.tsx` already compact the
  assistant experience but still leave room for higher-level status and
  demo-first prompts.
- `frontend/e2e/helpers/api.ts` and the existing E2E specs support isolated
  browser flows without live LLM calls.
- Scribe decisions confirm the current direction: dashboard-first desktop,
  secondary assistant, mobile-specific behavior, frontend-derived sectioning,
  no new section DB column, and Playwright as the browser reliability lane.
- Locus full-repo scan/impact was blocked by a permission-denied pytest temp
  directory. Narrowed Locus scans for `frontend/src`, `frontend/e2e`, and
  `backend/app/agent` completed; page/component impact checks reported low
  blast radius for `businesses/page.tsx`, `Workspace.tsx`, `ChatPanel.tsx`,
  `dashboardSections.ts`, and `workspaceBlackboard.tsx`. Treat this as useful
  directional context, not a complete dependency proof.

## Guiding Decisions

- Plan all DAMN demo polish together so the product gets a coherent story
  instead of disconnected visual tweaks.
- Execute in independently shippable phases. Each phase should leave E2E/CI
  green and preserve existing agent/dashboard contracts.
- Start with the highest visible mismatch: the `/businesses` launcher.
- Keep backend changes rare. Prefer existing dashboard, workspace, agent, and
  sandbox APIs unless a phase explicitly needs a new contract.
- Do not require live LLM calls for tests. Use existing direct REST helpers,
  ScriptedProvider, and deterministic offline data.
- Desktop demo polish can lead, but every phase must define graceful mobile
  behavior.
- Avoid expensive AWS dependencies. Deployment work should focus on checklists,
  reset safety, smoke tests, and teardown.

## Phase 0 - Current-State Audit And Guardrails

Status: completed in `docs/DEMO_POLISH_GUARDRAILS.md`.

### Goal

Lock down the current demo baseline before adding more polish.

### User/Demo Value

Prevents the next visual phase from accidentally regressing dashboard creation,
refresh persistence, Clean Layout, assistant flows, or offline demo data.

### Exact Feature Scope

- Capture a short visual/state audit of:
  - `/businesses`
  - `/businesses/[id]` desktop dashboard
  - `/businesses/[id]` mobile dashboard/chat
  - assistant open/collapsed states
  - empty workspace, populated workspace, and workspace error states
- Confirm local command lanes:
  - frontend unit/type/lint/format
  - backend focused agent tests
  - Playwright E2E
- Add any missing test IDs needed for later phases only if they are harmless.
- Record a small checklist in docs for what each later phase must re-check.

### Files Likely Affected

- `docs/ROADMAP_DEMO_POLISH.md`
- `docs/DEVELOPMENT.md` or README validation section, if checklist placement
  fits better there
- possibly no source files

### Backend Changes Needed

None.

### Frontend Changes Needed

None unless a missing `data-testid` blocks later E2E planning.

### Tests Needed

No new behavior tests required. Run existing focused suites and record current
gaps.

### E2E Coverage Needed

Run the existing Playwright suite locally. Do not expand it in this phase
unless selectors are already insufficient.

### Risks

- Spending too long auditing instead of moving to visible product polish.
- Treating screenshots as a source of truth without preserving automated tests.

### What NOT To Do

- Do not redesign UI.
- Do not change agent tools or workspace contracts.
- Do not add new infrastructure.

### Acceptance Criteria

- Existing validation lanes are known and documented.
- Current dashboard, assistant, Clean Layout, and offline demo paths are
  confirmed runnable.
- Any current test gaps are explicitly listed for later phases.

### Suggested Implementation Prompt

```text
Implement Phase 0 from docs/ROADMAP_DEMO_POLISH.md only. Do not redesign UI.
Run the current focused validation lanes, document the demo smoke checklist,
and add only harmless test IDs if needed for upcoming Playwright coverage.
```

## Phase 1 - Premium Business Launcher Redesign

### Goal

Turn `/businesses` from a plain list into a premium business insight
workspace launcher.

### User/Demo Value

The first authenticated screen should immediately feel like the same product as
the polished dashboard. In demos, this page should make the recommended sample
business obvious and explain the offline demo story without verbal setup.

### Exact Feature Scope

- Replace the narrow list layout with a full-width launcher shell that matches
  the dashboard visual language.
- Add a top hero band with:
  - "Your business insight workspaces" framing
  - short product context
  - primary action area for add/import or offline sample mode
  - small trust/status indicators such as offline mode, sample catalog, and
    deterministic demo data
- Redesign business cards into richer workspace tiles:
  - business name/type/address
  - rating and review count
  - analysis/demo-ready status derived from available fields
  - last-updated or "needs analysis" state where data exists
  - prominent "Open workspace" action
  - restrained delete action
- Add a recommended demo business treatment, especially for
  `sim_lager_ale_tlv` or the strongest available offline scenario.
- Polish `SandboxCatalog`:
  - scenario cards instead of dense rows
  - main business vs competitors visually clear
  - imported/open states clearer
  - compact variant still useful below existing workspaces
- Improve empty and error states with the same visual system as the dashboard.

### Files Likely Affected

- `frontend/src/app/businesses/page.tsx`
- `frontend/src/components/BusinessCard.tsx`
- `frontend/src/components/SandboxCatalog.tsx`
- `frontend/src/lib/types.ts` if existing type names need clarification only
- `frontend/e2e/*` for launcher coverage

### Backend Changes Needed

Avoid backend changes in the first pass. Use existing `Business` and
`CatalogResponse` fields. If richer health previews require analysis summaries
later, plan that separately.

### Frontend Changes Needed

- New responsive layout and card composition.
- Shared local helper functions for demo readiness labels and status.
- Stable test IDs for launcher, business tile, recommended demo tile, sandbox
  scenario card, import/open action, and reset action.

### Tests Needed

- Component-level or unit tests only if logic is extracted for status labels.
- Existing frontend unit/type/lint/format must pass.

### E2E Coverage Needed

- Authenticated user sees launcher.
- Offline catalog import creates or opens a sample workspace.
- Existing business tile opens `/businesses/[id]`.
- Empty state and compact catalog remain visible.

### Risks

- Overloading `BusinessCard` with fake health data not backed by the API.
- Making offline-only copy confusing for real provider mode.
- Introducing a marketing landing page instead of a useful workspace launcher.

### What NOT To Do

- Do not add analytics summaries to the business list API in this phase.
- Do not change authentication or business creation behavior.
- Do not redesign the dashboard at the same time.

### Acceptance Criteria

- `/businesses` visually matches the dashboard quality.
- A demo user can identify and open the best sample workspace in one click.
- Real provider add-business flow still works.
- Offline demo mode is clear and polished.
- E2E covers the launcher path without live LLM calls.

### Suggested Implementation Prompt

```text
Implement Phase 1 from docs/ROADMAP_DEMO_POLISH.md only: redesign /businesses
as a premium workspace launcher. Do not touch dashboard internals or backend
contracts. Preserve add/import/delete behavior and add focused Playwright
coverage for opening/importing a workspace.
```

## Phase 2 - Presentation Mode

### Goal

Add a demo-first dashboard presentation mode for clean walkthroughs and
interviews.

### User/Demo Value

Lets the dashboard shift from working mode to show mode: fewer controls, larger
insight hierarchy, less debug noise, and a clear exit path.

### Exact Feature Scope

- Add a presentation mode state on the business detail page.
- Entry points:
  - header action
  - later command bar integration
- Presentation mode should:
  - hide drag handles and delete buttons
  - hide or minimize assistant drawer
  - hide non-essential debug/dev clutter
  - keep executive summary prominent
  - enlarge or emphasize the hero section
  - keep sections readable in fullscreen-like layout
  - include "Exit presentation mode"
  - optionally include "Copy summary" if it can use existing dashboard text
- Desktop first. Mobile should degrade to a clean read-only dashboard mode.

### Files Likely Affected

- `frontend/src/app/businesses/[id]/page.tsx`
- `frontend/src/components/agent/Workspace.tsx`
- `frontend/src/components/agent/SortableWidgetCard.tsx`
- `frontend/src/components/agent/ExecutiveSummary.tsx`
- `frontend/e2e/dashboard-presentation.spec.ts`

### Backend Changes Needed

None.

### Frontend Changes Needed

- Presentation mode boolean and prop threading.
- Read-only display variant for workspace cards.
- Potential CSS utility classes for presentation sizing.
- Local storage persistence is optional; default should not surprise users.

### Tests Needed

- Unit or component tests for controls hidden in presentation mode if practical.
- Type/lint/format/build.

### E2E Coverage Needed

- Enter presentation mode.
- Drag/delete controls are hidden.
- Executive summary and sections remain visible.
- Exit restores working controls.
- Refresh behavior is explicitly decided and tested if persisted.

### Risks

- Prop drilling across dashboard components can get noisy.
- Hiding controls must not disable underlying state or break E2E selectors for
  normal mode.
- Fullscreen browser APIs can add permission/browser edge cases; avoid them in
  first pass.

### What NOT To Do

- Do not use native fullscreen API initially.
- Do not change widget persistence or reorder semantics.
- Do not add sharing URLs or public dashboards.

### Acceptance Criteria

- Presentation mode is visually distinct and cleaner.
- Work mode behavior is unchanged after exit.
- Desktop demo looks intentional at common viewport sizes.
- Mobile remains usable and does not overlap controls/text.

### Suggested Implementation Prompt

```text
Implement Phase 2 from docs/ROADMAP_DEMO_POLISH.md only: add dashboard
Presentation Mode. Keep it frontend-only, avoid native fullscreen APIs, hide
editing controls in presentation mode, and add Playwright coverage for
enter/exit and control visibility.
```

## Phase 3 - Command Bar And Quick Actions

### Goal

Add a demo-friendly command surface that reduces long prompt typing during live
walkthroughs.

### User/Demo Value

During a demo, the presenter can trigger high-value actions quickly: build demo
dashboard, Clean Layout, Presentation Mode, show issues, show positives, compare
recently, clear and rebuild.

### Exact Feature Scope

- Add a command bar or compact quick-action strip on the business detail page.
- Include actions:
  - Build demo dashboard
  - Clean layout
  - Presentation mode
  - Show top issues
  - Show positives
  - Compare last 30 days
  - Clear and rebuild
- Actions should reuse existing agent behavior by sending prompt text through
  `useAgentChat` where appropriate.
- Pure UI actions such as Clean Layout and Presentation Mode should call local
  handlers directly.
- Keep command labels short and demo-safe.

### Files Likely Affected

- new `frontend/src/components/agent/CommandBar.tsx` or similar
- `frontend/src/app/businesses/[id]/page.tsx`
- `frontend/src/components/agent/ChatPanel.tsx` or `useAgentChat` if command
  sending needs a lifted callback
- `frontend/src/components/agent/SuggestedPrompts.tsx`
- E2E specs for command actions

### Backend Changes Needed

Avoid new backend tools. Existing `clear_dashboard`, `pin_widget`,
`set_dashboard_order`, and data tools should handle command prompts.

### Frontend Changes Needed

- Clear ownership of who sends agent prompts. Prefer lifting `sendMessage`
  through a small context or controlled callback instead of duplicating chat
  state.
- Disabled/busy states while streaming.
- Optional keyboard shortcut only if discoverable and not risky.

### Tests Needed

- Reducer/hook tests only if command sending changes `useAgentChat`.
- Component tests for action availability if logic grows.

### E2E Coverage Needed

- Command sends "Build demo dashboard" via ScriptedProvider and widgets appear.
- Clean Layout command reuses existing reorder path.
- Presentation Mode command toggles local mode.
- Clear and rebuild command clears previous widgets before new ones.

### Risks

- Accidentally creating a second chat state path.
- Quick actions could trigger expensive/live LLM calls in tests if not routed
  through ScriptedProvider.
- Too many buttons can clutter the dashboard header.

### What NOT To Do

- Do not build a global app-wide command palette yet.
- Do not add new agent tools unless an existing behavior is impossible.
- Do not require keyboard shortcuts for success.

### Acceptance Criteria

- Common demo actions are one click.
- Chat transcript remains coherent after command-triggered prompts.
- Existing manual chat input still works.
- No live LLM dependency in tests.

### Suggested Implementation Prompt

```text
Implement Phase 3 from docs/ROADMAP_DEMO_POLISH.md only: add a business-detail
command bar/quick actions surface. Reuse existing agent prompts/tools and local
handlers. Do not create a second chat state path. Add deterministic Playwright
coverage with ScriptedProvider.
```

## Phase 4 - Narrative Insight Callouts

### Goal

Make the dashboard feel smarter by adding data-backed interpretation blocks,
not just charts.

### User/Demo Value

The dashboard should answer "so what?" immediately: what changed, main risk,
best opportunity, and what to do next.

### Exact Feature Scope

- Add dashboard-level executive brief cards based on existing `Dashboard`
  fields:
  - What changed
  - Main risk
  - Best opportunity
  - What to do next
- Add section-level callout slots where enough data exists.
- Use existing analysis fields first:
  - `ai_summary`
  - `recommended_focus`
  - `top_complaints`
  - `top_praise`
  - `action_items`
  - `risk_flags`, if available in current types
- Show "needs analysis" or omit blocks when data is missing. Do not invent
  values.
- Consider extracting pure selectors from `Dashboard` to a frontend utility.

### Files Likely Affected

- new `frontend/src/components/agent/NarrativeCallouts.tsx`
- `frontend/src/components/agent/ExecutiveSummary.tsx`
- `frontend/src/components/agent/Workspace.tsx`
- `frontend/src/lib/types.ts`
- `frontend/src/lib/__tests__/...` for selectors

### Backend Changes Needed

None in first pass. If existing dashboard payload cannot support a desired
callout honestly, defer that callout.

### Frontend Changes Needed

- Pure data-backed callout selectors.
- Responsive callout layout.
- Integration into executive summary or workspace sections.

### Tests Needed

- Unit tests for selector behavior with full, partial, and empty analysis.
- Component tests if display states become complex.

### E2E Coverage Needed

- Seed/fixture dashboard with analysis fields and assert callouts render.
- Empty/no-analysis business does not show fake insights.

### Risks

- Fake or overconfident interpretation if data is missing.
- Too many narrative blocks can compete with actual charts/widgets.

### What NOT To Do

- Do not call the LLM from the frontend.
- Do not add backend-generated narrative fields until existing fields are
  exhausted.
- Do not show placeholder "insights" as if they are real.

### Acceptance Criteria

- Dashboard has clear, data-backed narrative interpretation.
- Missing data is handled honestly.
- Callouts improve scanability without crowding the canvas.

### Suggested Implementation Prompt

```text
Implement Phase 4 from docs/ROADMAP_DEMO_POLISH.md only: add data-backed
narrative insight callouts using existing dashboard fields. Do not add LLM calls
or fake placeholders. Add selector tests for full and partial data.
```

## Phase 5 - Motion And Transition Polish

### Goal

Make the app feel alive with tasteful, accessible motion.

### User/Demo Value

Dashboard rebuilds, Clean Layout, assistant interactions, and chart loading
should feel deliberate instead of abrupt.

### Exact Feature Scope

- Refine existing motion utilities in `frontend/src/app/globals.css`.
- Add or improve:
  - widget entry animation
  - dashboard clear/rebuild transition
  - Clean Layout feedback
  - assistant drawer open/close
  - KPI count-up or subtle load effect
  - chart reveal
  - hover/focus states
  - skeletons where loading is real
- Respect `prefers-reduced-motion`.
- Keep animation durations short and consistent.

### Files Likely Affected

- `frontend/src/app/globals.css`
- `frontend/src/components/agent/Workspace.tsx`
- `frontend/src/components/agent/ExecutiveSummary.tsx`
- chart widgets under `frontend/src/components/agent/widgets/`
- possibly `/businesses` launcher components from Phase 1

### Backend Changes Needed

None.

### Frontend Changes Needed

- CSS utilities and component class updates.
- Optional small hook for count-up only if it remains deterministic and
  reduced-motion aware.

### Tests Needed

- Unit tests only for any hook logic.
- Visual/manual QA is more important here.
- Ensure no hydration issues from animated counters.

### E2E Coverage Needed

- Keep E2E functional assertions stable. Avoid timing-sensitive animation
  assertions.
- Optional reduced-motion smoke only if a helper is simple.

### Risks

- Animation can make E2E flaky if assertions depend on final layout too soon.
- Over-animation can make the product feel less serious.

### What NOT To Do

- Do not introduce a large animation library.
- Do not animate layout dimensions in ways that shift text unexpectedly.
- Do not make tests wait on arbitrary timeouts.

### Acceptance Criteria

- Motion is subtle, consistent, and respects reduced motion.
- Existing E2E stays stable.
- No text overlap or layout jump in desktop/mobile smoke checks.

### Suggested Implementation Prompt

```text
Implement Phase 5 from docs/ROADMAP_DEMO_POLISH.md only: polish motion and
transitions with CSS/local utilities, respect prefers-reduced-motion, and avoid
timing-sensitive E2E assertions.
```

## Phase 6 - Assistant Experience Polish

### Goal

Make the assistant read like a premium copilot instead of a chat/debug log.

### User/Demo Value

The assistant should clearly communicate working state, completed actions, and
recovered issues while staying secondary to the dashboard.

### Exact Feature Scope

- Improve assistant header/status:
  - idle
  - thinking
  - working with tools
  - done
  - error/recovered
- Further compact activity traces:
  - group multi-tool runs when possible
  - keep technical details expandable
  - summarize successful actions cleanly
- Refine preview cards and `+ Dashboard` affordance.
- Align quick prompt chips with Phase 3 command language.
- Consider a "last action completed" summary near the input.

### Files Likely Affected

- `frontend/src/components/agent/ChatPanel.tsx`
- `frontend/src/components/agent/ChatMessage.tsx`
- `frontend/src/components/agent/ToolCallIndicator.tsx`
- `frontend/src/components/agent/SuggestedPrompts.tsx`
- `frontend/src/lib/useAgentChat.ts`
- `frontend/src/lib/__tests__/useAgentChat.reducer.test.ts`
- `frontend/src/components/agent/__tests__/spinner.test.tsx`

### Backend Changes Needed

Avoid backend changes. Existing SSE events should be enough for UI status.

### Frontend Changes Needed

- Derive clear status from `items`, `isStreaming`, and current tool calls.
- Improve message surfaces and activity rows.
- Keep recovered errors muted but inspectable.

### Tests Needed

- Reducer/render tests for:
  - thinking/working/done states
  - recovered failure row
  - clear/reorder/pin compact confirmations

### E2E Coverage Needed

- Existing agent add/recover/remove/duplicate specs should still pass.
- Add one focused assistant status E2E only if it is stable under
  ScriptedProvider.

### Risks

- Over-abstracting message rendering.
- Accidentally hiding useful error details during debugging.
- Making the assistant too visually dominant on desktop.

### What NOT To Do

- Do not redesign the whole chat protocol.
- Do not remove raw details entirely; keep them expandable.
- Do not change backend SSE payloads unless a real frontend gap exists.

### Acceptance Criteria

- Assistant status is understandable at a glance.
- Successful actions are summarized cleanly.
- Recovered failures do not dominate the transcript.
- Existing agent flows and chat history persistence still pass.

### Suggested Implementation Prompt

```text
Implement Phase 6 from docs/ROADMAP_DEMO_POLISH.md only: polish assistant
status, compact activity traces, recovered errors, and preview cards. Avoid
backend protocol changes unless absolutely necessary.
```

## Phase 7 - Final Dashboard Composition Upgrades

### Goal

Refine the dashboard composition beyond the current sectioned layout.

### User/Demo Value

The dashboard should feel like a composed analysis product, not just organized
cards.

### Exact Feature Scope

- Strengthen the hero row:
  - dominant chart or narrative insight
  - supporting KPI/brief next to it
- Improve business overview as a real insight panel.
- Further differentiate:
  - action/recommendation cards
  - chart cards
  - evidence/review cards
  - narrative summary cards
- Improve visual grouping between related widgets.
- Use desktop width more effectively without creating crowded cards.
- Apply mobile-specific dashboard polish:
  - section rhythm
  - chart readability
  - assistant access

### Files Likely Affected

- `frontend/src/components/agent/Workspace.tsx`
- `frontend/src/components/agent/SortableWidgetCard.tsx`
- `frontend/src/components/agent/WidgetRenderer.tsx`
- widgets under `frontend/src/components/agent/widgets/`
- `frontend/src/lib/dashboardSections.ts`
- dashboard E2E specs

### Backend Changes Needed

None for first pass. If hero selection requires stored preferences later, plan a
separate schema/tool change.

### Frontend Changes Needed

- More explicit composition rules for hero/supporting widgets.
- Stronger per-widget-kind layout constraints.
- Potential utility for choosing hero widget.

### Tests Needed

- Unit tests for hero selection/composition logic.
- Widget rendering tests for new visual variants if logic changes.

### E2E Coverage Needed

- Dashboard with mixed widgets renders hero/supporting layout.
- Clean Layout still preserves data and order.
- Mobile dashboard remains readable.

### Risks

- Layout logic can become too clever and surprise users.
- Cross-section drag/reorder expectations may become unclear.

### What NOT To Do

- Do not add user-editable layout schema in this phase.
- Do not break the flat persisted position model.
- Do not force every widget into a hero layout.

### Acceptance Criteria

- Dashboard has a stronger first-read hierarchy.
- Widget families remain distinct and coherent.
- Existing Clean Layout and drag/reorder behavior still work.
- Desktop and mobile layouts avoid overlap and cramped text.

### Suggested Implementation Prompt

```text
Implement Phase 7 from docs/ROADMAP_DEMO_POLISH.md only: improve dashboard
composition and hero/supporting layout while preserving flat widget persistence
and Clean Layout behavior. Add unit and E2E coverage for the composition rules.
```

## Phase 8 - Demo Hardening, Reset, And Cost-Aware Deployment

### Goal

Make the final demo repeatable, safe, and cheap to run.

### User/Demo Value

Before interviews or live demos, there should be a clear path to reset data,
verify the app, present it, and tear down paid resources.

### Exact Feature Scope

- Final deploy smoke checklist:
  - auth
  - `/businesses` launcher
  - offline sample import/open
  - fetch/re-analyze
  - build demo dashboard
  - Clean Layout
  - Presentation Mode
  - assistant command path
  - refresh persistence
- AWS cost teardown checklist after demo.
- Optional one-command demo reset if it can safely reuse existing sandbox reset
  and offline data.
- Ensure demo data remains stable and documented.
- Confirm CI/E2E green.
- Document what must not use live LLM in tests.

### Files Likely Affected

- README
- `docs/DEVELOPMENT.md`
- new `docs/DEMO_RUNBOOK.md` if warranted
- `Makefile` only if adding a safe reset/smoke command
- scripts only if reset/smoke automation is small and safe

### Backend Changes Needed

Avoid backend changes unless a reset endpoint already exists and only needs a
thin documented wrapper.

### Frontend Changes Needed

None unless smoke checklist exposes a small UI issue.

### Tests Needed

- Run full intended validation lane.
- Add script tests only if new automation is added.

### E2E Coverage Needed

- Full Playwright suite.
- Optional one "demo happy path" if not redundant with existing specs.

### Risks

- Accidentally adding destructive reset commands without clear safeguards.
- Over-investing in AWS automation for a short-lived demo.
- Running paid resources longer than needed.

### What NOT To Do

- Do not add expensive AWS dependencies.
- Do not create destructive commands without explicit confirmation.
- Do not require live LLM for CI/E2E.

### Acceptance Criteria

- Demo runbook is clear enough to follow under time pressure.
- Reset and teardown steps are explicit.
- CI/E2E status is known.
- The demo can be repeated without manual guesswork.

### Suggested Implementation Prompt

```text
Implement Phase 8 from docs/ROADMAP_DEMO_POLISH.md only: create the final demo
runbook, reset/teardown checklist, and any small safe automation. Do not add
expensive infrastructure or destructive commands without confirmation.
```

## Recommended First Implementation Phase

Start with Phase 1 after Phase 0 is either completed or explicitly waived.

Reasoning:

- The `/businesses` launcher is the most visible stale surface.
- It has high demo impact before the user reaches the dashboard.
- It is mostly frontend-contained and lower risk than changing dashboard
  contracts.
- It establishes the visual language for later command/presentation work.
- It improves both real use and offline demo flow.

## Main Roadmap Risks

- Visual polish could outrun test coverage. Every phase needs a focused test
  lane.
- Dashboard and assistant changes can regress existing agent flows if phases
  touch `useAgentChat`, workspace events, or widget persistence casually.
- Narrative callouts can become fake if they are not strictly data-backed.
- Motion can introduce E2E flake if assertions depend on animation timing.
- Command actions can accidentally duplicate chat state or bypass the normal
  agent flow.
- Demo reset/deployment work can become destructive or expensive if not kept
  explicit and opt-in.

## Phase Order Summary

1. Stabilize/current-state audit
2. Premium `/businesses` launcher redesign
3. Presentation Mode
4. Command bar and quick actions
5. Narrative insight callouts
6. Motion and transition polish
7. Assistant experience polish
8. Final dashboard composition upgrades
9. Demo hardening, reset, and cost-aware deployment

This order intentionally fixes the entry-point mismatch first, then adds demo
presentation controls, then improves interpretation and feel, and only then
does final hardening. It avoids one large rewrite while still preserving one
coherent product direction.
