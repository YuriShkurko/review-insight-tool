/**
 * Scenarios A + B: agent adds a widget with data; refresh preserves widget + chat history.
 *
 * Driven entirely by deterministic backend state — no live LLM, no waiting on
 * UI animations beyond Playwright's web-first auto-waits.
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

test.describe("Scenario A: agent adds widget with data", () => {
  test("agent prompt → widget appears with chart data, no empty state", async ({
    page,
    context,
    request,
  }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("add_widget_with_data.json"));

    await gotoBusiness(page, user);
    const ui = dashboard(page);

    // Workspace starts empty (no pinned widgets) — sanity check on the testid.
    await expect(ui.getByTestId("workspace-empty-state")).toBeVisible();

    await ui.getByTestId("agent-input").fill("Show me a rating distribution");
    await ui.getByTestId("agent-send").click();

    // The agent's pin_widget tool emits a workspace_event SSE → blackboard
    // appends the widget; the workspace card renders immediately.
    const widget = ui.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Rating distribution");
    await expect(widget).toHaveAttribute("data-widget-type", "bar_chart");

    // Hard guarantee that the widget is not stuck in the "no chart data
    // available." empty state — that was the v3.6.x regression class.
    await expect(widget.getByTestId("widget-empty-state")).toHaveCount(0);

    // Chart container must contain an SVG with bar geometry — proves data
    // actually rendered, not just an empty wrapper.
    await expect(widget.getByTestId("widget-chart").locator("svg rect")).not.toHaveCount(0);
  });
});

test.describe("Scenario B: refresh preserves widget data and chat history", () => {
  test("widget + user message + assistant text survive a full reload", async ({
    page,
    context,
    request,
  }) => {
    const user = await seedUser(request);
    await injectAuthToken(context, user.token);
    await setAgentScript(request, loadScriptFixture("add_widget_with_data.json"));
    await gotoBusiness(page, user);
    const ui = dashboard(page);

    const userPrompt = "Show me a rating distribution";
    await ui.getByTestId("agent-input").fill(userPrompt);
    await ui.getByTestId("agent-send").click();

    // Wait for the streaming round-trip to finish — the input becomes
    // re-enabled when isStreaming flips back to false.
    await expect(ui.getByTestId("agent-input")).toBeEnabled();
    await expect(ui.getByTestId("workspace-widget")).toHaveCount(1);

    // Final assistant text turn from the script.
    await expect(
      ui
        .getByTestId("chat-message")
        .filter({ hasText: "Added rating distribution to the dashboard." }),
    ).toBeVisible();

    // Refresh the whole page.
    await page.reload();
    const ui2 = dashboard(page);

    // Widget persists via the GET /agent/workspace fetch on mount.
    const widget = ui2.getByTestId("workspace-widget");
    await expect(widget).toHaveCount(1);
    await expect(widget.getByTestId("widget-title")).toHaveText("Rating distribution");
    await expect(widget.getByTestId("widget-empty-state")).toHaveCount(0);

    // Chat restores from the persisted conversation (localStorage conv_<biz_id>
    // → GET /agent/conversations/{id}).
    await expect(ui2.getByTestId("chat-message").filter({ hasText: userPrompt })).toBeVisible();
    await expect(
      ui2
        .getByTestId("chat-message")
        .filter({ hasText: "Added rating distribution to the dashboard." }),
    ).toBeVisible();
  });
});
