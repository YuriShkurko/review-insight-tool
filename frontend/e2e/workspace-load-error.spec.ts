/**
 * Scenario G: workspace load endpoint fails → error banner + retry, NOT the
 * empty state. Reproduces the v3.6.x dashboard-block bug from the user's
 * perspective (the error UI is what tells them to refresh, not silence).
 */

import { test, expect } from "@playwright/test";
import { dashboard, gotoBusiness, injectAuthToken, seedUser } from "./helpers/api";

test("workspace load failure shows error banner with retry, not empty state", async ({
  page,
  context,
  request,
}) => {
  const user = await seedUser(request);
  await injectAuthToken(context, user.token);

  const workspaceUrl = `**/api/businesses/${user.businessId}/agent/workspace`;

  // Always-500 mock for the workspace GET. We can't switch behavior on the
  // first vs second call because React strict-mode (Next.js dev) double-
  // invokes the mounting useEffect, so any "first request fails, second
  // succeeds" trick races the strict-mode double-mount and the error UI
  // never appears. Keeping it simple: fail every time, then unroute when we
  // are ready for retry to succeed.
  await page.route(workspaceUrl, async (route) => {
    if (route.request().method() !== "GET") {
      await route.continue();
      return;
    }
    await route.fulfill({
      status: 500,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Simulated backend failure" }),
    });
  });

  await gotoBusiness(page, user);
  const ui = dashboard(page);

  await expect(ui.getByTestId("workspace-error-banner")).toBeVisible();
  await expect(ui.getByTestId("workspace-empty-state")).toHaveCount(0);

  const retryButton = ui.getByTestId("retry-workspace-button");
  await expect(retryButton).toBeVisible();

  // Drop the route mock so the retry hits the real backend (empty workspace).
  await page.unroute(workspaceUrl);
  await retryButton.click();

  await expect(ui.getByTestId("workspace-error-banner")).toHaveCount(0);
  await expect(ui.getByTestId("workspace-empty-state")).toBeVisible();
});
