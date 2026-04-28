import { describe, it, expect } from "vitest";
import { workspaceReducer, type WorkspaceState } from "../workspaceBlackboard";
import type { WorkspaceWidget } from "../agentTypes";

const INITIAL: WorkspaceState = {
  widgets: [],
  isLoading: false,
  error: null,
};

function widget(id: string, position: number): WorkspaceWidget {
  return {
    id,
    widget_type: "summary_card",
    title: `Widget ${id}`,
    data: { summary: id },
    position,
    created_at: "2026-04-28T00:00:00Z",
  };
}

describe("workspaceReducer", () => {
  it("deduplicates WIDGET_ADDED by id", () => {
    const existing = widget("w1", 0);
    const state = workspaceReducer(
      { ...INITIAL, widgets: [existing] },
      {
        type: "WIDGET_ADDED",
        widget: { ...existing, title: "Updated copy" },
      },
    );

    expect(state.widgets).toHaveLength(1);
    expect(state.widgets[0].title).toBe("Widget w1");
  });

  it("appends a new WIDGET_ADDED item", () => {
    const state = workspaceReducer(
      { ...INITIAL, widgets: [widget("w1", 0)] },
      {
        type: "WIDGET_ADDED",
        widget: widget("w2", 1),
      },
    );

    expect(state.widgets.map((w) => w.id)).toEqual(["w1", "w2"]);
  });

  it("removes widgets by id", () => {
    const state = workspaceReducer(
      { ...INITIAL, widgets: [widget("w1", 0), widget("w2", 1)] },
      {
        type: "WIDGET_REMOVED",
        widgetId: "w1",
      },
    );

    expect(state.widgets.map((w) => w.id)).toEqual(["w2"]);
  });

  it("reorders requested widgets and preserves unspecified widgets after them", () => {
    const state = workspaceReducer(
      { ...INITIAL, widgets: [widget("w1", 0), widget("w2", 1), widget("w3", 2)] },
      { type: "WIDGET_REORDERED", widgetIds: ["w3", "w1"] },
    );

    expect(state.widgets.map((w) => w.id)).toEqual(["w3", "w1", "w2"]);
  });
});
