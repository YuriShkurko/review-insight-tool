import { describe, it, expect } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { createElement } from "react";
import {
  workspaceReducer,
  workspaceLoadErrorMessage,
  type WorkspaceState,
} from "../workspaceBlackboard";
import { ApiError } from "../api";
import { dispatchWorkspaceEvent } from "../useAgentChat";
import { WidgetRenderer } from "../../components/agent/WidgetRenderer";
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
  it("does not hide existing widgets during a reconciliation reload", () => {
    const existing = widget("w1", 0);
    const state = workspaceReducer(
      { ...INITIAL, widgets: [existing] },
      {
        type: "INIT_LOAD",
      },
    );

    expect(state.isLoading).toBe(false);
    expect(state.error).toBeNull();
    expect(state.widgets).toEqual([existing]);
  });

  it("preserves existing widgets when a reload fails", () => {
    const existing = widget("w1", 0);
    const state = workspaceReducer(
      { ...INITIAL, widgets: [existing] },
      {
        type: "LOAD_ERROR",
        error: "Network error. Please check your connection.",
      },
    );

    expect(state.isLoading).toBe(false);
    expect(state.error).toBe("Network error. Please check your connection.");
    expect(state.widgets).toEqual([existing]);
  });

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

  it("keeps duplicate widgets with identical data when ids differ", () => {
    const sharedData = {
      bars: [{ label: "slow service", value: 4 }],
      total: 4,
    };
    const first: WorkspaceWidget = {
      id: "original-widget",
      widget_type: "bar_chart",
      title: "Top issues",
      data: sharedData,
      position: 0,
      created_at: "2026-04-28T00:00:00Z",
    };
    const copy: WorkspaceWidget = {
      ...first,
      id: "copied-widget",
      title: "Top issues (copy)",
      position: 1,
    };

    const state = workspaceReducer(
      workspaceReducer({ ...INITIAL }, { type: "WIDGET_ADDED", widget: first }),
      { type: "WIDGET_ADDED", widget: copy },
    );

    expect(state.widgets).toHaveLength(2);
    expect(state.widgets.map((w) => w.id)).toEqual(["original-widget", "copied-widget"]);
    expect(state.widgets.map((w) => w.data)).toEqual([sharedData, sharedData]);

    const html = renderToStaticMarkup(
      createElement(
        "div",
        null,
        state.widgets.map((w) =>
          createElement(
            "section",
            { key: w.id, "data-widget-id": w.id },
            createElement("h2", null, w.title),
            createElement(WidgetRenderer, { widgetType: w.widget_type, data: w.data }),
          ),
        ),
      ),
    );
    expect(html).toContain("original-widget");
    expect(html).toContain("copied-widget");
    expect(html).toContain("Top issues (copy)");
    expect(html.match(/slow service/g)).toHaveLength(4);
    expect(html).not.toContain("No chart data available.");
  });

  it("normalizes blackboard-added widgets and makes them renderable immediately", () => {
    const state = workspaceReducer(
      { ...INITIAL, isLoading: true },
      {
        type: "WIDGET_ADDED",
        widget: {
          id: "w1",
          widgetType: "donut_chart",
          title: "Rating share",
          data: { slices: [{ label: "5 star", value: 4, percent: 80 }] },
          position: "2",
          createdAt: "2026-04-28T00:00:00Z",
        } as never,
      },
    );

    expect(state.isLoading).toBe(false);
    expect(state.widgets[0]).toMatchObject({
      id: "w1",
      widget_type: "donut_chart",
      title: "Rating share",
      position: 2,
      data: { slices: [{ label: "5 star", value: 4, percent: 80 }] },
    });
    const html = renderToStaticMarkup(
      WidgetRenderer({ widgetType: state.widgets[0].widget_type, data: state.widgets[0].data }),
    );
    expect(html).toContain("5 star");
    expect(html).not.toContain("No chart data available.");
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

  it("ignores WIDGET_REMOVED for an unknown id", () => {
    const before = [widget("w1", 0), widget("w2", 1)];
    const state = workspaceReducer(
      { ...INITIAL, widgets: before },
      {
        type: "WIDGET_REMOVED",
        widgetId: "missing",
      },
    );

    expect(state.widgets.map((w) => w.id)).toEqual(["w1", "w2"]);
  });

  it("dispatches widget_removed workspace events to the reducer action", () => {
    const actions: unknown[] = [];

    dispatchWorkspaceEvent({ action: "widget_removed", widget_id: "w1" }, (action) =>
      actions.push(action),
    );

    expect(actions).toEqual([{ type: "WIDGET_REMOVED", widgetId: "w1" }]);
  });

  it("dispatches widgets_reordered workspace events to the reducer action", () => {
    const actions: unknown[] = [];

    dispatchWorkspaceEvent({ action: "widgets_reordered", widget_ids: ["w3", "w1"] }, (action) =>
      actions.push(action),
    );

    expect(actions).toEqual([{ type: "WIDGET_REORDERED", widgetIds: ["w3", "w1"] }]);
  });

  it("dispatches dashboard_cleared workspace events to the reducer action", () => {
    const actions: unknown[] = [];

    dispatchWorkspaceEvent({ action: "dashboard_cleared", widget_ids: ["w1", "w2"] }, (action) =>
      actions.push(action),
    );

    expect(actions).toEqual([{ type: "DASHBOARD_CLEARED" }]);
  });

  it("reorders requested widgets and preserves unspecified widgets after them", () => {
    const state = workspaceReducer(
      { ...INITIAL, widgets: [widget("w1", 0), widget("w2", 1), widget("w3", 2)] },
      { type: "WIDGET_REORDERED", widgetIds: ["w3", "w1"] },
    );

    expect(state.widgets.map((w) => w.id)).toEqual(["w3", "w1", "w2"]);
  });

  it("WIDGET_REORDERED updates position fields so sort-by-position preserves drop order", () => {
    const before = [widget("w1", 0), widget("w2", 1), widget("w3", 2)];
    const state = workspaceReducer(
      { ...INITIAL, widgets: before },
      { type: "WIDGET_REORDERED", widgetIds: ["w3", "w1", "w2"] },
    );

    // Positions must be reassigned sequentially so sort-by-position gives the dropped order.
    expect(state.widgets.find((w) => w.id === "w3")?.position).toBe(0);
    expect(state.widgets.find((w) => w.id === "w1")?.position).toBe(1);
    expect(state.widgets.find((w) => w.id === "w2")?.position).toBe(2);

    // Sort-by-position (as Workspace.tsx does) must equal the dropped order.
    const sorted = [...state.widgets].sort((a, b) => a.position - b.position);
    expect(sorted.map((w) => w.id)).toEqual(["w3", "w1", "w2"]);
  });

  it("agent auto-add with empty data produces a widget with the correct type and graceful empty state", () => {
    const state = workspaceReducer(
      { ...INITIAL },
      {
        type: "WIDGET_ADDED",
        widget: {
          id: "w-empty",
          widget_type: "bar_chart",
          title: "Rating distribution",
          data: {},
          position: 0,
          created_at: "2026-04-28T00:00:00Z",
        },
      },
    );

    expect(state.widgets[0].widget_type).toBe("bar_chart");
    // Empty data shows an empty state, not a rendering crash.
    const html = renderToStaticMarkup(
      WidgetRenderer({ widgetType: state.widgets[0].widget_type, data: state.widgets[0].data }),
    );
    expect(html).toContain("No chart data available.");
    expect(html).not.toContain("undefined");
    expect(html).not.toContain("null");
  });

  it("WIDGET_REMOVED clears stale error so deleting the last widget does not lock the dashboard", () => {
    const before: WorkspaceState = {
      ...INITIAL,
      error: "Server error: Something went wrong.",
      widgets: [widget("w1", 0)],
    };
    const state = workspaceReducer(before, { type: "WIDGET_REMOVED", widgetId: "w1" });

    expect(state.widgets).toEqual([]);
    expect(state.error).toBeNull();
  });

  it("DASHBOARD_CLEARED removes every widget and clears stale error", () => {
    const before: WorkspaceState = {
      ...INITIAL,
      error: "Server error: Something went wrong.",
      widgets: [widget("w1", 0), widget("w2", 1)],
    };
    const state = workspaceReducer(before, { type: "DASHBOARD_CLEARED" });

    expect(state.widgets).toEqual([]);
    expect(state.error).toBeNull();
    expect(state.isLoading).toBe(false);
  });

  it("CLEAR_ERROR drops the banner without touching widgets", () => {
    const before: WorkspaceState = {
      ...INITIAL,
      error: "Server error: Something went wrong.",
      widgets: [widget("w1", 0)],
    };
    const state = workspaceReducer(before, { type: "CLEAR_ERROR" });

    expect(state.widgets).toEqual([widget("w1", 0)]);
    expect(state.error).toBeNull();
  });

  it("workspaceLoadErrorMessage classifies common HTTP failures", () => {
    expect(workspaceLoadErrorMessage(new ApiError(0, "Network error."))).toBe(
      "Network: Network error.",
    );
    expect(workspaceLoadErrorMessage(new ApiError(401, "Session expired."))).toBe(
      "Unauthorized: Session expired.",
    );
    expect(workspaceLoadErrorMessage(new ApiError(403, "Forbidden."))).toBe(
      "Forbidden: Forbidden.",
    );
    expect(workspaceLoadErrorMessage(new ApiError(404, "Not found."))).toBe(
      "Not found: Not found.",
    );
    expect(workspaceLoadErrorMessage(new ApiError(422, "Bad payload."))).toBe(
      "Validation: Bad payload.",
    );
    expect(workspaceLoadErrorMessage(new ApiError(503, "Backend down."))).toBe(
      "Server error: Backend down.",
    );
    expect(workspaceLoadErrorMessage(new Error("nope"))).toBe("Failed to load workspace.");
  });

  it("auto-add and manual-add produce identical normalized shapes for the same raw payload", () => {
    const raw = {
      id: "w1",
      widget_type: "line_chart",
      title: "Review Trend",
      data: { series: [{ date: "2026-04-01", count: 3 }], metric: "count" },
      position: 0,
      created_at: "2026-04-28T00:00:00Z",
    };

    // Simulate manual-add path (POST response → normalizeWorkspaceWidget → WIDGET_ADDED)
    const stateManual = workspaceReducer({ ...INITIAL }, { type: "WIDGET_ADDED", widget: raw });

    // Simulate agent auto-add path (workspace_event SSE → normalizeWorkspaceWidget → WIDGET_ADDED)
    const stateAuto = workspaceReducer({ ...INITIAL }, { type: "WIDGET_ADDED", widget: raw });

    expect(stateManual.widgets[0]).toEqual(stateAuto.widgets[0]);
    // Both must have the required render fields.
    for (const w of [stateManual.widgets[0], stateAuto.widgets[0]]) {
      expect(w).toHaveProperty("id");
      expect(w).toHaveProperty("widget_type");
      expect(w).toHaveProperty("title");
      expect(w).toHaveProperty("data");
      expect(w).toHaveProperty("position");
    }
  });
});
