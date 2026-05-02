/**
 * Clean layout: clicking "Clean layout" groups widgets by section and
 * persists the order after refresh.
 */

import { test, expect } from "@playwright/test";
import {
  dashboard,
  gotoBusiness,
  injectAuthToken,
  pinWidgetDirect,
  seedUser,
} from "./helpers/api";

test("Clean layout groups widgets by section and persists after refresh", async ({
  page,
  context,
  request,
}) => {
  const user = await seedUser(request);
  await injectAuthToken(context, user.token);

  // Pin a chart first, then a metric card — deliberately mixed order.
  const chart = await pinWidgetDirect(request, user, "line_chart", "Rating Trend", {
    labels: ["Mon", "Tue"],
    values: [4.1, 4.3],
  });
  const metric = await pinWidgetDirect(request, user, "metric_card", "Avg Rating", {
    value: 4.2,
  });

  await gotoBusiness(page, user);
  const ui = dashboard(page);

  // Both widgets should be visible.
  await expect(ui.getByTestId("workspace-widget")).toHaveCount(2);

  // No widget data lost, no duplicates.
  const titles = await ui.getByTestId("widget-title").allTextContents();
  expect(titles.sort()).toEqual(["Avg Rating", "Rating Trend"].sort());

  // Click Clean layout.
  await ui.getByTestId("clean-layout-button").click();

  // After clean layout: Overview section (metric_card) should appear before Trends (line_chart).
  const overviewSection = ui.getByTestId("workspace-section-overview");
  const trendsSection = ui.getByTestId("workspace-section-trends");
  await expect(overviewSection).toBeVisible();
  await expect(trendsSection).toBeVisible();

  const overviewBox = await overviewSection.boundingBox();
  const trendsBox = await trendsSection.boundingBox();
  expect(overviewBox!.y).toBeLessThan(trendsBox!.y);

  // No widget data lost after reorder.
  await expect(ui.getByTestId("workspace-widget")).toHaveCount(2);
  const titlesAfter = await ui.getByTestId("widget-title").allTextContents();
  expect(titlesAfter.sort()).toEqual(["Avg Rating", "Rating Trend"].sort());

  // Reload and assert order persists.
  await page.reload();
  const ui2 = dashboard(page);
  await expect(ui2.getByTestId("workspace-widget")).toHaveCount(2);
  const overviewAfterReload = ui2.getByTestId("workspace-section-overview");
  const trendsAfterReload = ui2.getByTestId("workspace-section-trends");
  await expect(overviewAfterReload).toBeVisible();
  await expect(trendsAfterReload).toBeVisible();

  const overviewBoxReload = await overviewAfterReload.boundingBox();
  const trendsBoxReload = await trendsAfterReload.boundingBox();
  expect(overviewBoxReload!.y).toBeLessThan(trendsBoxReload!.y);

  void chart;
  void metric;
});
