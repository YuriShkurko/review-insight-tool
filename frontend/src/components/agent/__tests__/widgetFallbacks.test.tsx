import { renderToStaticMarkup } from "react-dom/server";
import { describe, it, expect } from "vitest";
import { WidgetRenderer } from "../WidgetRenderer";
import { SummaryCard } from "../widgets/SummaryCard";

describe("widget fallbacks", () => {
  it("renders an unsupported widget type message instead of raw JSON", () => {
    const html = renderToStaticMarkup(
      <WidgetRenderer widgetType="pie_chart" data={{ value: 1 }} />,
    );

    expect(html).toContain("Unsupported widget type");
    expect(html).toContain("pie_chart");
    expect(html).not.toContain("&quot;value&quot;");
  });

  it("renders a summary fallback when data is empty", () => {
    const html = renderToStaticMarkup(<SummaryCard data={{}} />);

    expect(html).toContain("No summary data available.");
  });
});
