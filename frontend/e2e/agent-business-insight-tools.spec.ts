/**
 * Scenarios H + I: Business Insight core tools — health score and signal timeline.
 *
 * Driven by ScriptedProvider; no live LLM. The actual tool implementations
 * run against real (mock) review data seeded by seedUser.
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

test.describe("Scenario H: business health score widget", () => {
  test("agent pins health_score widget with score data", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("business_health.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("Show me the business health score");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Business Health");
    await expect(widget).toHaveAttribute("data-widget-type", "health_score");

    // HealthScore renders "{score}/100" — proves the score was computed and rendered.
    await expect(widget).toContainText("/100");
  });
});

test.describe("Scenario I: signal timeline widget", () => {
  test("agent pins signal_timeline widget with events", async ({ page, context, request }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("signal_timeline.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    await ui.getByTestId("agent-input").fill("What changed this week?");
    await ui.getByTestId("agent-send").click();

    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Signal Timeline");
    await expect(widget).toHaveAttribute("data-widget-type", "signal_timeline");

    // SignalTimeline renders events as an <ol>; at least one <li> must exist.
    await expect(widget.locator("ol li")).not.toHaveCount(0);
  });
});
