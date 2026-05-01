/**
 * Scenario D: duplicate/copy chart creates two widgets, both with data.
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

test("agent duplicates a chart and both copies render with data", async ({
  page,
  context,
  request,
}) => {
  const user = await seedUser(request);
  await injectAuthToken(context, user.token);

  // Seed a bar_chart widget with real data.
  const realData = {
    bars: [
      { label: "5★", value: 7 },
      { label: "1★", value: 2 },
    ],
    total: 9,
  };
  const source = await pinWidgetDirect(request, user, "bar_chart", "Top issues", realData);

  await setAgentScript(
    request,
    loadScriptFixture("duplicate_widget.json", { WIDGET_ID: source.id }),
  );

  await gotoBusiness(page, user);
  const ui = dashboard(page);
  await expect(ui.getByTestId("workspace-widget")).toHaveCount(1);

  await ui.getByTestId("agent-input").fill("make a copy of the top issues chart");
  await ui.getByTestId("agent-send").click();

  const widgets = ui.getByTestId("workspace-widget");
  await expect(widgets).toHaveCount(2);

  // Both widgets must have actual chart geometry (not the empty-state text).
  for (let i = 0; i < 2; i++) {
    const w = widgets.nth(i);
    await expect(w.getByTestId("widget-empty-state")).toHaveCount(0);
    await expect(w.getByTestId("widget-chart").locator("svg rect")).not.toHaveCount(0);
  }

  // Refresh — both still present.
  await page.reload();
  const ui2 = dashboard(page);
  const widgets2 = ui2.getByTestId("workspace-widget");
  await expect(widgets2).toHaveCount(2);
  for (let i = 0; i < 2; i++) {
    await expect(widgets2.nth(i).getByTestId("widget-empty-state")).toHaveCount(0);
  }
});
