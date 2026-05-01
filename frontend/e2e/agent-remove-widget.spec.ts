/**
 * Scenario C: agent removes a widget; refresh keeps it removed.
 */

import { test, expect } from "@playwright/test";
import {
  dashboard,
  gotoBusiness,
  injectAuthToken,
  loadScriptFixture,
  pinWidgetDirect,
  seedUser,
  setAgentScript,
} from "./helpers/api";

test("agent removes widget and refresh keeps it removed", async ({ page, context, request }) => {
  const user = await seedUser(request);
  await injectAuthToken(context, user.token);

  // Seed an existing widget so we have a known UUID to target.
  const seeded = await pinWidgetDirect(request, user, "metric_card", "Avg rating", { value: 4.2 });

  await setAgentScript(request, loadScriptFixture("remove_widget.json", { WIDGET_ID: seeded.id }));

  await gotoBusiness(page, user);
  const ui = dashboard(page);
  await expect(ui.getByTestId("workspace-widget")).toHaveCount(1);

  await ui.getByTestId("agent-input").fill("remove that widget");
  await ui.getByTestId("agent-send").click();

  await expect(ui.getByTestId("workspace-widget")).toHaveCount(0);
  await expect(ui.getByTestId("workspace-empty-state")).toBeVisible();

  await page.reload();
  const ui2 = dashboard(page);
  await expect(ui2.getByTestId("workspace-widget")).toHaveCount(0);
  await expect(ui2.getByTestId("workspace-empty-state")).toBeVisible();
});
