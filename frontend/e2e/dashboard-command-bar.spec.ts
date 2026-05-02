/**
 * Phase 3: command bar quick actions reuse the normal agent chat/workspace
 * paths and local presentation/clean-layout handlers.
 */

import { test, expect } from "@playwright/test";
import { dashboard } from "./helpers/api";
import {
  MOCK_BUSINESS_ID,
  lineWidget,
  metricWidget,
  mockBusinessDetailApi,
  prepareMockAuth,
} from "./helpers/mockApi";

test("command bar sends agent prompt and pins resulting widget", async ({ page, context }) => {
  await mockBusinessDetailApi(page);
  await prepareMockAuth(context);

  await page.goto(`/businesses/${MOCK_BUSINESS_ID}`);
  const ui = dashboard(page);

  await expect(page.getByTestId("command-bar")).toBeVisible();
  await page.getByTestId("command-build-demo-dashboard").click();

  await expect(ui.getByTestId("workspace-widget")).toHaveCount(1);
  await expect(ui.getByTestId("widget-title")).toHaveText("Rating distribution");
  await expect(ui.getByTestId("widget-empty-state")).toHaveCount(0);
});

test("command bar clean layout and presentation actions use local dashboard handlers", async ({
  page,
  context,
}) => {
  await mockBusinessDetailApi(page, {
    initialWidgets: [
      { ...lineWidget(), position: 0 },
      { ...metricWidget(), position: 1 },
    ],
  });
  await prepareMockAuth(context);

  await page.goto(`/businesses/${MOCK_BUSINESS_ID}`);
  const ui = dashboard(page);

  await expect(ui.getByTestId("workspace-widget")).toHaveCount(2);
  await page.getByTestId("command-clean-layout").click();

  const overviewSection = ui.getByTestId("workspace-section-overview");
  const trendsSection = ui.getByTestId("workspace-section-trends");
  await expect(overviewSection).toBeVisible();
  await expect(trendsSection).toBeVisible();

  const overviewBox = await overviewSection.boundingBox();
  const trendsBox = await trendsSection.boundingBox();
  expect(overviewBox!.y).toBeLessThan(trendsBox!.y);

  await page.getByTestId("command-presentation-mode").click();

  await expect(ui.getByTestId("presentation-mode-badge")).toBeVisible();
  await expect(page.getByTestId("command-bar")).toHaveCount(0);
  await expect(ui.getByTestId("remove-widget-button")).toHaveCount(0);
});
