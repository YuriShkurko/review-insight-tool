# Demo Runbook

Use this before interviews, walkthroughs, or production-like demos. The goal is a repeatable, low-risk path from setup to teardown without live LLM dependencies in tests or accidental AWS spend.

## 1. Pre-Demo Readiness

Confirm the intended mode first:

- Local deterministic demo: backend uses `REVIEW_PROVIDER=mock` or `offline`, and tests use `LLM_PROVIDER=scripted`.
- AWS demo: backend task definition uses `REVIEW_PROVIDER=offline`; confirm all paid resources are intentional and scheduled for teardown.
- Browser target: validate desktop Chrome first, then one mobile viewport.

Run the focused non-browser validation lane:

```bash
cd frontend
npx.cmd tsc --noEmit
npx.cmd vitest run src/lib/__tests__/narrativeCallouts.test.ts src/lib/__tests__/dashboardSections.test.ts src/lib/__tests__/workspaceBlackboard.test.ts src/components/agent/__tests__/spinner.test.tsx src/components/agent/widgets/__tests__/WidgetRenderer.test.tsx src/components/agent/widgets/__tests__/LineChart.test.ts
npm.cmd run lint
```

## 2. Browser Smoke

Start the deterministic E2E harness when a local database is available:

```bash
# Terminal 1
make test-e2e-servers

# Terminal 2
cd frontend
npm run test:e2e -- e2e/business-launcher.spec.ts e2e/dashboard-presentation.spec.ts e2e/dashboard-command-bar.spec.ts
```

Manual smoke checklist:

- Sign in and land on `/businesses`.
- Confirm the premium launcher loads and a workspace tile opens `/businesses/[id]`.
- In offline mode, import a catalog sample and verify the action changes to `Open workspace`.
- Fetch or refresh reviews, then run analysis.
- Use `Build demo dashboard` from the command bar and confirm widgets appear.
- Use `Clean Layout`; refresh and confirm order/data persist.
- Enter `Presentation Mode`; editing controls and assistant drawer should be hidden. Exit and confirm controls return.
- Ask the assistant for top issues or positives; confirm status text, tool traces, preview cards, and `+ Dashboard` still work.
- Check mobile width: launcher cards, dashboard tabs, presentation mode, and chart text should not overlap.

## 3. Safe Demo Reset

Prefer UI reset in offline mode:

1. Open `/businesses`.
2. Use `Reset offline samples`.
3. Re-import the intended sample, usually Lager & Ale.
4. Re-run fetch/analyze and rebuild the dashboard.

For MCP/debug reset, only use the guarded offline reset tool when `REVIEW_PROVIDER=offline` and you are targeting the correct demo user. It must require explicit confirmation and must not affect non-sandbox businesses.

Do not add or run broad database reset commands for a live demo unless the database is disposable.

## 4. AWS Demo Smoke

Before showing an AWS deployment:

- Confirm the ALB/frontend URL loads over the expected protocol.
- Register or sign in with the demo account.
- Confirm `/api/bootstrap` reports the expected review provider.
- Import/open an offline sample.
- Fetch reviews, run analysis, build dashboard, Clean Layout, Presentation Mode, and refresh persistence.
- Confirm no test path uses a real OpenAI/OpenRouter key.

## 5. Cost-Aware Teardown

After the demo, record whether AWS resources should stay up. If not, tear them down promptly:

```bash
make aws-status
make aws-teardown
```

Then verify:

- ECS services are no longer running.
- ALB is deleted.
- RDS or other paid databases are deleted or intentionally retained.
- CloudWatch/log retention is acceptable.
- Any temporary secrets or demo credentials are rotated if they were shared.

## 6. Known Caveats

- Playwright requires the local E2E server harness and a reachable disposable database.
- Full-repo Locus scans can still be blocked by local pytest temp directory permissions; focused frontend scans are acceptable for this roadmap.
- Presentation and command-bar specs are added but should be browser-executed before relying on a live demo.
