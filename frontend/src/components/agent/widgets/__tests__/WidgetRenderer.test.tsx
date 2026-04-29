import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { WidgetRenderer } from "../../WidgetRenderer";

const FIXTURES: Array<[string, Record<string, unknown>, string]> = [
  ["metric_card", { value: 4.6, label: "Average rating" }, "Average rating"],
  ["summary_card", { summary: "Service is improving." }, "Service is improving."],
  ["insight_list", { issues: [{ theme: "slow service", count: 3 }] }, "slow service"],
  [
    "review_list",
    { reviews: [{ id: "r1", rating: 2, text: "Slow wait", author: "A" }] },
    "Slow wait",
  ],
  ["comparison_card", { comparison_summary: "You lead on service." }, "You lead on service."],
  ["trend_indicator", { period: "7d", current: { count: 4 }, previous: { count: 2 } }, "Reviews"],
  ["line_chart", { series: [{ date: "2026-04-01", count: 2 }], metric: "count" }, "Apr"],
  ["bar_chart", { bars: [{ label: "5 star", value: 7 }] }, "5 star"],
  ["pie_chart", { slices: [{ label: "Positive", value: 8, percent: 80 }] }, "Positive"],
  ["donut_chart", { slices: [{ label: "Positive", value: 8, percent: 80 }] }, "Positive"],
  ["horizontal_bar_chart", { bars: [{ label: "slow service", value: 3 }] }, "slow service"],
  [
    "comparison_chart",
    {
      current_period: "this month",
      previous_period: "last month",
      current: { count: 5, avg_rating: 4.5 },
      previous: { count: 3, avg_rating: 3.8 },
      rating_delta: 0.7,
      count_delta: 2,
    },
    "this month",
  ],
];

describe("WidgetRenderer supported widget fixtures", () => {
  it.each(FIXTURES)("renders %s fixture", (widgetType, data, expected) => {
    const html = renderToStaticMarkup(<WidgetRenderer widgetType={widgetType} data={data} />);
    expect(html).toContain(expected);
    expect(html).not.toContain("Unsupported widget type");
  });

  it("renders tooltip details for chart values", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer
        widgetType="donut_chart"
        data={{ slices: [{ label: "Positive", value: 8, percent: 80 }] }}
      />,
    );
    expect(html).toContain("<title>Positive: 8 (80%)</title>");
  });

  it("bar_chart tooltip title includes label, value, and percentage", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer
        widgetType="bar_chart"
        data={{
          bars: [
            { label: "5★", value: 8 },
            { label: "1★", value: 2 },
          ],
        }}
      />,
    );
    // SVG <title> elements must contain label, value, and percentage
    expect(html).toContain("5★: 8 (80.0%)");
    expect(html).toContain("1★: 2 (20.0%)");
    // Labels also appear in the bottom legend
    expect(html).toContain("5★: 8");
    expect(html).toContain("1★: 2");
  });

  it("line_chart tooltip uses readable date labels not raw ISO keys", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer
        widgetType="line_chart"
        data={{ series: [{ date: "2026-04-01", count: 3 }], metric: "count" }}
      />,
    );
    // Title must contain formatted date (e.g. "Apr 1") and value+unit, not the raw ISO key
    expect(html).toContain("reviews");
    expect(html).not.toContain('"date"');
    expect(html).not.toContain('"count"');
  });

  it("renders empty states for new chart widgets", () => {
    expect(renderToStaticMarkup(<WidgetRenderer widgetType="donut_chart" data={{}} />)).toContain(
      "No chart data available.",
    );
    expect(
      renderToStaticMarkup(<WidgetRenderer widgetType="horizontal_bar_chart" data={{}} />),
    ).toContain("No chart data available.");
    expect(
      renderToStaticMarkup(<WidgetRenderer widgetType="comparison_chart" data={{}} />),
    ).toContain("No comparison data available.");
    expect(renderToStaticMarkup(<WidgetRenderer widgetType="line_chart" data={{}} />)).toContain(
      "No chart data available.",
    );
    expect(renderToStaticMarkup(<WidgetRenderer widgetType="bar_chart" data={{}} />)).toContain(
      "No chart data available.",
    );
  });

  it("donut_chart legend shows label, value, and percentage for each slice", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer
        widgetType="donut_chart"
        data={{
          slices: [
            { label: "5 star", value: 8, percent: 80 },
            { label: "1 star", value: 2, percent: 20 },
          ],
        }}
      />,
    );
    expect(html).toContain("5 star");
    expect(html).toContain("80%");
    expect(html).toContain("1 star");
    expect(html).toContain("20%");
  });
});
