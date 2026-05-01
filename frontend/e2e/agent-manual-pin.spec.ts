/**
 * Scenario F: agent surfaces a tool-result preview in chat, user clicks the
 * "+ Dashboard" pin button manually. Validates the manual-add path that
 * bypasses the agent's pin_widget tool.
 */

import { test, expect } from "@playwright/test";
import { dashboard, gotoBusiness, injectAuthToken, seedUser, setAgentScript } from "./helpers/api";

test("user can manually pin a tool-result preview from chat", async ({
  page,
  context,
  request,
}) => {
  const user = await seedUser(request);
  await injectAuthToken(context, user.token);

  // Script that ONLY produces a data-tool result + assistant text — no
  // pin_widget call. The user must press the manual pin button to get a
  // dashboard widget.
  await setAgentScript(request, [
    {
      text: "",
      tool_calls: [{ name: "get_dashboard", arguments: {} }],
    },
    {
      text: "Here's a dashboard summary you can pin if you want.",
      tool_calls: [],
    },
  ]);

  await gotoBusiness(page, user);
  const ui = dashboard(page);
  await expect(ui.getByTestId("workspace-empty-state")).toBeVisible();

  await ui.getByTestId("agent-input").fill("show me a dashboard summary");
  await ui.getByTestId("agent-send").click();

  // The tool-result preview is a collapsed <details> — expand it so the
  // manual pin button becomes interactable. The preview <summary> is
  // identifiable by the "preview" hint text the chat renders.
  const previewSummary = ui.locator("summary", { hasText: /preview/i }).first();
  await expect(previewSummary).toBeVisible();
  await previewSummary.click();

  const pinButton = ui.getByTestId("pin-widget-button");
  await expect(pinButton).toBeVisible();
  await pinButton.click();

  const widget = ui.getByTestId("workspace-widget");
  await expect(widget).toHaveCount(1);
  await expect(widget).toHaveAttribute("data-widget-type", "summary_card");
  await expect(widget.getByTestId("widget-empty-state")).toHaveCount(0);
});
