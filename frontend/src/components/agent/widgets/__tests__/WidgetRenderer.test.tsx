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
    "health_score",
    {
      score: 72,
      label: "Business Health",
      confidence: "medium",
      source: "reviews_and_analysis",
      sub_scores: [{ id: "reputation", label: "Reputation", score: 84 }],
      drivers: ["Average rating is 4.20 across 24 reviews."],
      risks: ["2 complaint themes are present."],
      opportunities: ["Fix rush-hour wait time."],
    },
    "Business Health",
  ],
  [
    "signal_timeline",
    {
      period: "past 30 days",
      summary: "Found 2 timeline signals.",
      events: [
        {
          id: "rating-change",
          date: "2026-05-01",
          severity: "critical",
          title: "Average rating dropped",
          summary: "Average rating moved from 4.6 to 3.8.",
          impact: "This is large enough to change customer perception.",
        },
      ],
    },
    "Average rating dropped",
  ],
  [
    "sales_summary",
    {
      label: "Demo Sales Summary",
      summary: "Demo POS-lite signals show 500 orders.",
      is_demo: true,
      source: "demo_sales",
      confidence: "demo",
      metrics: [{ label: "Revenue", value: 12000, unit: "USD" }],
      items: [{ label: "Beer / drinks", value: 52, unit: "%" }],
      recommendation: "Compare demand spikes with review complaints.",
    },
    "Demo signal",
  ],
  [
    "operations_risk",
    {
      label: "Demo Operations Risk",
      summary: "Demo operations signals show 18 minute estimated waits.",
      metrics: [{ label: "Estimated wait", value: 18, unit: "min" }],
      recommendation: "Staff the peak window first.",
    },
    "Estimated wait",
  ],
  [
    "local_presence_card",
    {
      label: "Demo Local Presence",
      summary: "Demo local presence signals show 2,000 profile views.",
      metrics: [{ label: "Views", value: 2000, unit: "views" }],
    },
    "Demo Local Presence",
  ],
  [
    "social_signal",
    {
      label: "Demo Social Signals",
      summary: "Demo social signals show 55 local mentions.",
      metrics: [{ label: "Mentions", value: 55, unit: "mentions" }],
    },
    "Demo Social Signals",
  ],
  [
    "opportunity_list",
    {
      summary: "Prioritized opportunities from review evidence.",
      opportunities: [
        {
          id: "fix-primary-friction",
          title: "Fix slow wait",
          evidence: "slow wait appears in analysis.",
          recommended_action: "Add one more server during rush.",
          priority: "high",
          impact: "high",
          effort: "medium",
          metric_to_watch: "Low-rating review share",
        },
      ],
    },
    "Fix slow wait",
  ],
  [
    "action_plan",
    {
      summary: "A short action plan for the next operating cycle.",
      actions: [
        {
          id: "fix-primary-friction",
          rank: 1,
          issue_or_opportunity: "Fix slow wait",
          evidence: "slow wait appears in analysis.",
          recommended_action: "Add one more server during rush.",
          suggested_owner: "General manager",
          metric_to_watch: "Low-rating review share",
        },
      ],
    },
    "General manager",
  ],
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
  [
    "money_flow",
    {
      revenue: 9000,
      cogs: 2700,
      operating_expenses: 3150,
      net_profit: 3150,
      currency: "USD",
      period: "Last 30 days",
      is_demo: true,
    },
    "$9,000",
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

  it("money_flow computes gross profit and shows margin", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer
        widgetType="money_flow"
        data={{ revenue: 10000, cogs: 3000, operating_expenses: 4000, currency: "USD" }}
      />,
    );
    expect(html).toContain("Gross Profit");
    expect(html).toContain("Net Profit");
    expect(html).toContain("70% margin");
    expect(html).toContain("30% margin");
    expect(html).not.toContain("Ranking");
  });

  it("money_flow shows empty state when no revenue", () => {
    const html = renderToStaticMarkup(<WidgetRenderer widgetType="money_flow" data={{}} />);
    expect(html).toContain("No financial flow data available.");
  });

  it("money_flow is not mapped to unsupported widget type", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer widgetType="money_flow" data={{ revenue: 5000 }} />,
    );
    expect(html).not.toContain("Unsupported widget type");
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
