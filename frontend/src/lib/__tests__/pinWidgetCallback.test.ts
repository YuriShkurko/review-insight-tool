import { describe, it, expect } from "vitest";
import { dispatchWorkspaceEvent, shouldTriggerWidgetPinned } from "../useAgentChat";
import type { WorkspaceAction } from "../workspaceBlackboard";

describe("shouldTriggerWidgetPinned", () => {
  it("returns true for pin_widget with pinned=true", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", { pinned: true })).toBe(true);
  });

  it("returns false for pin_widget with pinned=false", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", { pinned: false })).toBe(false);
  });

  it("returns false for pin_widget with no pinned field", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", {})).toBe(false);
  });

  it("returns false for a different tool even if pinned=true", () => {
    expect(shouldTriggerWidgetPinned("get_dashboard", { pinned: true })).toBe(false);
  });

  it("returns false for pin_widget with pinned=1 (truthy but not boolean true)", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", { pinned: 1 })).toBe(false);
  });
});

describe("dispatchWorkspaceEvent", () => {
  it("dispatches WIDGET_ADDED for widget_added SSE payloads", () => {
    const actions: WorkspaceAction[] = [];
    const widget = {
      id: "w1",
      widget_type: "bar_chart",
      title: "Rating distribution",
      data: { bars: [] },
      position: 0,
      created_at: "2026-04-28T00:00:00Z",
    };

    dispatchWorkspaceEvent({ action: "widget_added", widget }, (action) => actions.push(action));

    expect(actions).toEqual([{ type: "WIDGET_ADDED", widget }]);
  });

  it("normalizes camelCase widget payloads from workspace_event", () => {
    const actions: WorkspaceAction[] = [];

    dispatchWorkspaceEvent(
      {
        action: "widget_added",
        widget: {
          id: "w1",
          widgetType: "donut_chart",
          title: "Rating share",
          data: { slices: [{ label: "5 star", value: 4 }] },
          position: 0,
          createdAt: "2026-04-28T00:00:00Z",
        },
      },
      (action) => actions.push(action),
    );

    expect(actions[0]).toMatchObject({
      type: "WIDGET_ADDED",
      widget: { id: "w1", widget_type: "donut_chart" },
    });
  });

  it("ignores unknown workspace events", () => {
    const actions: WorkspaceAction[] = [];

    dispatchWorkspaceEvent({ action: "unknown", widget: { id: "w1" } }, (action) =>
      actions.push(action),
    );

    expect(actions).toEqual([]);
  });
});
