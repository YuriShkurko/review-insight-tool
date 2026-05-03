/**
 * Scenarios J–M: Demo signal tools — sales, operations, local presence, social.
 *
 * All four use the SignalSummary renderer which stamps "Demo signal" when is_demo=true.
 * That badge is the key content assertion: it proves the demo provider ran and the
 * renderer received real data, not the "No signal data available." fallback.
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

test.describe("Scenario J: sales summary widget", () => {
  test("agent pins sales_summary with demo signal badge", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("sales_summary.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("Show me the sales summary");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Sales Summary");
    await expect(widget).toHaveAttribute("data-widget-type", "sales_summary");
    await expect(widget).toContainText("Demo signal");
  });
});

test.describe("Scenario K: operations risk widget", () => {
  test("agent pins operations_risk with demo signal badge", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("operations_risk.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("Show me operations risk");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Operations Risk");
    await expect(widget).toHaveAttribute("data-widget-type", "operations_risk");
    await expect(widget).toContainText("Demo signal");
  });
});

test.describe("Scenario L: local presence widget", () => {
  test("agent pins local_presence_card with demo signal badge", async ({
    page,
    context,
    request,
  }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("local_presence.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("Show me local presence");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Local Presence");
    await expect(widget).toHaveAttribute("data-widget-type", "local_presence_card");
    await expect(widget).toContainText("Demo signal");
  });
});

test.describe("Scenario M: social signal widget", () => {
  test("agent pins social_signal with demo signal badge", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("social_signal.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("Show me social signals");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Social Signals");
    await expect(widget).toHaveAttribute("data-widget-type", "social_signal");
    await expect(widget).toContainText("Demo signal");
  });
});
