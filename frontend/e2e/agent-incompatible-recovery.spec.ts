/**
 * Scenario E: incompatible chart request recovers via the rehydrated tool_results
 * registry — the failed pie pin produces no widget, the recovery turn pins a
 * compatible horizontal_bar_chart of the same data.
 */

import { test, expect } from "@playwright/test";
import {
  dashboard,
  gotoBusiness,
  injectAuthToken,
  loadScriptFixture,
  seedUser,
  setAgentScript,
} from "./helpers/api";

test("incompatible pie request → no empty widget, then recovers as horizontal_bar_chart", async ({
  page,
  context,
  request,
}) => {
  const user = await seedUser(request);
  await injectAuthToken(context, user.token);
  await setAgentScript(request, loadScriptFixture("incompatible_chart_recovery.json"));
  await gotoBusiness(page, user);
  const ui = dashboard(page);

  // Turn 1: ask for the pie chart that the executor will refuse.
  await ui.getByTestId("agent-input").fill("Pin a pie chart of top complaints");
  await ui.getByTestId("agent-send").click();

  // The recovery message comes back from the script; dashboard stays empty
  // because the pin was refused (no workspace_event ever fires).
  await expect(
    ui.getByTestId("chat-message").filter({ hasText: /try a bar chart/i }),
  ).toBeVisible();
  await expect(ui.getByTestId("workspace-widget")).toHaveCount(0);
  await expect(ui.getByTestId("workspace-empty-state")).toBeVisible();

  // Wait for the round-trip to finish before sending the recovery message.
  await expect(ui.getByTestId("agent-input")).toBeEnabled();

  // Turn 2: user accepts the recovery suggestion.
  await ui.getByTestId("agent-input").fill("yes use the bar chart");
  await ui.getByTestId("agent-send").click();

  const widget = ui.getByTestId("workspace-widget");
  await expect(widget).toHaveCount(1);
  await expect(widget).toHaveAttribute("data-widget-type", "horizontal_bar_chart");
  await expect(widget.getByTestId("widget-empty-state")).toHaveCount(0);
  await expect(
    ui.getByTestId("chat-message").filter({ hasText: /pinned the bar chart/i }),
  ).toBeVisible();
});
