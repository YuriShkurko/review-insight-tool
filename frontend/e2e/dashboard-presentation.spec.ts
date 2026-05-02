/**
 * Phase 2: Presentation Mode hides editing controls and assistant chrome,
 * then restores normal workspace controls after exit.
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

test("Presentation Mode hides editing controls and restores them after exit", async ({
  page,
  context,
}) => {
  await mockBusinessDetailApi(page, { initialWidgets: [metricWidget(), lineWidget()] });
  await prepareMockAuth(context);

  await page.goto(`/businesses/${MOCK_BUSINESS_ID}`);
  const ui = dashboard(page);

  await expect(ui.getByTestId("workspace-widget")).toHaveCount(2);
  await expect(ui.getByTestId("clean-layout-button")).toBeVisible();
  await expect(ui.getByTestId("remove-widget-button").first()).toBeVisible();
  await expect(ui.getByTestId("drag-widget-handle").first()).toBeVisible();
  await expect(ui.getByTestId("assistant-drawer")).toBeVisible();

  await page.getByTestId("presentation-mode-toggle").click();

  await expect(ui.getByTestId("presentation-mode-badge")).toBeVisible();
  await expect(ui.getByTestId("clean-layout-button")).toHaveCount(0);
  await expect(ui.getByTestId("remove-widget-button")).toHaveCount(0);
  await expect(ui.getByTestId("drag-widget-handle")).toHaveCount(0);
  await expect(ui.getByTestId("assistant-drawer")).toHaveCount(0);
  await expect(ui.getByTestId("executive-summary")).toBeVisible();
  await expect(ui.getByTestId("workspace-widget")).toHaveCount(2);

  await page.getByTestId("presentation-mode-toggle").click();

  await expect(ui.getByTestId("presentation-mode-badge")).toHaveCount(0);
  await expect(ui.getByTestId("clean-layout-button")).toBeVisible();
  await expect(ui.getByTestId("remove-widget-button").first()).toBeVisible();
  await expect(ui.getByTestId("drag-widget-handle").first()).toBeVisible();
  await expect(ui.getByTestId("assistant-drawer")).toBeVisible();
});
