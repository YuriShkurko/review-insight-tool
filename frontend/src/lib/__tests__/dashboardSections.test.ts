import { describe, it, expect } from "vitest";
import {
  classifyWidget,
  groupBySection,
  flattenForReorder,
  SECTIONS,
} from "../dashboardSections";
import type { WorkspaceWidget } from "../agentTypes";

function w(
  id: string,
  widget_type: string,
  title = "Test",
  data: Record<string, unknown> = {},
): WorkspaceWidget {
  return { id, widget_type, title, data, position: 0, created_at: "2026-01-01T00:00:00Z" };
}

describe("classifyWidget", () => {
  it("puts metric_card in overview", () => {
    expect(classifyWidget(w("1", "metric_card"))).toBe("overview");
  });

  it("puts trend_indicator in overview", () => {
    expect(classifyWidget(w("1", "trend_indicator"))).toBe("overview");
  });

  it("puts summary_card with ai_summary in overview", () => {
    expect(classifyWidget(w("1", "summary_card", "Summary", { ai_summary: "good" }))).toBe(
      "overview",
    );
  });

  it("puts summary_card with action_items in actions", () => {
    expect(
      classifyWidget(w("1", "summary_card", "Actions", { action_items: ["do this"] })),
    ).toBe("actions");
  });

  it("puts summary_card with recommended_focus in actions", () => {
    expect(
      classifyWidget(w("1", "summary_card", "Focus", { recommended_focus: "service" })),
    ).toBe("actions");
  });

  it("puts line_chart in trends", () => {
    expect(classifyWidget(w("1", "line_chart"))).toBe("trends");
  });

  it("puts bar_chart in trends", () => {
    expect(classifyWidget(w("1", "bar_chart"))).toBe("trends");
  });

  it("puts horizontal_bar_chart in trends", () => {
    expect(classifyWidget(w("1", "horizontal_bar_chart"))).toBe("trends");
  });

  it("puts comparison_chart in trends", () => {
    expect(classifyWidget(w("1", "comparison_chart"))).toBe("trends");
  });

  it("puts comparison_card in trends", () => {
    expect(classifyWidget(w("1", "comparison_card"))).toBe("trends");
  });

  it("puts pie_chart in issues", () => {
    expect(classifyWidget(w("1", "pie_chart"))).toBe("issues");
  });

  it("puts donut_chart in issues", () => {
    expect(classifyWidget(w("1", "donut_chart"))).toBe("issues");
  });

  it("puts insight_list with default title in issues", () => {
    expect(classifyWidget(w("1", "insight_list", "Top Themes"))).toBe("issues");
  });

  it("puts insight_list with action in title in actions", () => {
    expect(classifyWidget(w("1", "insight_list", "Recommended Actions"))).toBe("actions");
  });

  it("puts insight_list with recommend in title in actions", () => {
    expect(classifyWidget(w("1", "insight_list", "Top Recommendations"))).toBe("actions");
  });

  it("puts review_list in evidence", () => {
    expect(classifyWidget(w("1", "review_list"))).toBe("evidence");
  });

  it("fallback unknown type goes to overview", () => {
    expect(classifyWidget(w("1", "unknown_widget_xyz"))).toBe("overview");
  });
});

describe("groupBySection", () => {
  it("groups widgets into correct sections", () => {
    const widgets = [
      w("a", "metric_card"),
      w("b", "line_chart"),
      w("c", "pie_chart"),
      w("d", "review_list"),
      w("e", "insight_list", "Action Plan", { action_items: [] }),
    ];
    const grouped = groupBySection(widgets);
    expect(grouped.overview.map((x) => x.id)).toEqual(["a"]);
    expect(grouped.trends.map((x) => x.id)).toEqual(["b"]);
    expect(grouped.issues.map((x) => x.id)).toEqual(["c"]);
    expect(grouped.evidence.map((x) => x.id)).toEqual(["d"]);
    expect(grouped.actions.map((x) => x.id)).toEqual(["e"]);
  });

  it("returns empty arrays for empty sections", () => {
    const grouped = groupBySection([]);
    for (const s of SECTIONS) {
      expect(grouped[s]).toEqual([]);
    }
  });

  it("preserves position order within each section", () => {
    const widgets = [
      { ...w("b", "metric_card"), position: 1 },
      { ...w("a", "metric_card"), position: 0 },
    ];
    const sorted = [...widgets].sort((x, y) => x.position - y.position);
    const grouped = groupBySection(sorted);
    expect(grouped.overview.map((x) => x.id)).toEqual(["a", "b"]);
  });
});

describe("flattenForReorder", () => {
  it("produces IDs in section order", () => {
    const widgets = [
      w("chart1", "line_chart"),
      w("metric1", "metric_card"),
      w("review1", "review_list"),
    ];
    const grouped = groupBySection(widgets);
    const flat = flattenForReorder(grouped);
    expect(flat).toEqual(["metric1", "chart1", "review1"]);
  });

  it("round-trips group → flatten without losing IDs", () => {
    const widgets = [
      w("a", "metric_card"),
      w("b", "line_chart"),
      w("c", "pie_chart"),
      w("d", "review_list"),
    ];
    const grouped = groupBySection(widgets);
    const flat = flattenForReorder(grouped);
    expect(flat.sort()).toEqual(["a", "b", "c", "d"].sort());
    expect(flat.length).toBe(4);
  });

  it("empty grouped produces empty array", () => {
    const grouped = groupBySection([]);
    expect(flattenForReorder(grouped)).toEqual([]);
  });
});
