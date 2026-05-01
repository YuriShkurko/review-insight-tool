import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright config for the Review Insight agent/dashboard E2E suite.
 *
 * Both servers must be running before `npx playwright test` is invoked:
 *   Backend: TESTING=true LLM_PROVIDER=scripted REVIEW_PROVIDER=mock
 *            uvicorn app.main:app --port 8000
 *   Frontend: NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
 *
 * Use `make test-e2e-ui` from the repo root to start both with the right env
 * and run the suite (see Makefile). The harness intentionally does not use
 * Playwright's `webServer` block — these are real long-running servers we
 * already have orchestration for, and re-spawning them per-suite is brittle
 * on Windows.
 */
export default defineConfig({
  testDir: "./e2e",
  testMatch: /.*\.spec\.ts$/,
  timeout: 30_000,
  expect: { timeout: 10_000 },
  fullyParallel: false, // shared backend ScriptedProvider singleton — keep serial
  workers: 1,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: process.env.CI ? [["list"], ["github"]] : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    actionTimeout: 8_000,
    navigationTimeout: 15_000,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
