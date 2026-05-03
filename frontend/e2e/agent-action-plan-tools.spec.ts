/**
 * Scenarios N + O: Action-plan tools — opportunity list and action plan.
 *
 * Both use the ActionPlan renderer. The opportunity_list widget renders under
 * "Opportunities" and action_plan under "Action Plan". Content assertion checks
 * that at least one plan item rendered (the item container div).
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

test.describe("Scenario N: opportunity list widget", () => {
  test("agent pins opportunity_list with ranked items", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("opportunity_list.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("What are my top opportunities?");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Opportunities");
    await expect(widget).toHaveAttribute("data-widget-type", "opportunity_list");

    // ActionPlan renderer wraps each item in a rounded border div inside a space-y-2 container.
    // At least one item must exist — proves data rendered, not the fallback.
    await expect(widget.locator(".space-y-2 > div")).not.toHaveCount(0);
  });
});

test.describe("Scenario O: action plan widget", () => {
  test("agent pins action_plan with ranked actions", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("action_plan.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("What should I do this week?");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Action Plan");
    await expect(widget).toHaveAttribute("data-widget-type", "action_plan");

    // Same structure as opportunity_list — item divs inside the space-y-2 container.
    await expect(widget.locator(".space-y-2 > div")).not.toHaveCount(0);
  });
});
