import { MetricCard } from "./widgets/MetricCard";
import { BarChart } from "./widgets/BarChart";
import { LineChart } from "./widgets/LineChart";
import { SummaryCard } from "./widgets/SummaryCard";
import { TrendIndicator } from "./widgets/TrendIndicator";
import { DonutChart } from "./widgets/DonutChart";
import { HorizontalBarChart } from "./widgets/HorizontalBarChart";
import { ComparisonChart } from "./widgets/ComparisonChart";

type ReviewRow = {
  id: string;
  rating: number;
  text: string | null;
  author: string | null;
  published_at: string | null;
};

function ReviewListWidget({ data }: { data: Record<string, unknown> }) {
  const reviews = data.reviews as ReviewRow[] | undefined;
  if (!reviews?.length) return <p className="text-xs text-text-muted">No reviews found.</p>;
  return (
    <div className="space-y-2 max-h-52 overflow-y-auto pr-1">
      {reviews.map((r) => (
        <div key={r.id} className="border-b border-border-subtle last:border-0 pb-2 last:pb-0">
          <div className="flex items-center gap-1.5 mb-0.5">
            <span className="text-yellow-400 text-xs tracking-tighter">
              {"*".repeat(r.rating)}
              {"-".repeat(5 - r.rating)}
            </span>
            {r.author && <span className="text-xs text-text-muted">{r.author}</span>}
          </div>
          {r.text && <p className="text-xs text-text-secondary line-clamp-2">{r.text}</p>}
        </div>
      ))}
    </div>
  );
}

function ComparisonWidget({ data }: { data: Record<string, unknown> }) {
  const summary = data.comparison_summary as string | null | undefined;
  const strengths = data.strengths as string[] | undefined;
  const weaknesses = data.weaknesses as string[] | undefined;
  const opportunities = data.opportunities as string[] | undefined;

  return (
    <div className="space-y-3 text-xs">
      {summary && <p className="text-text-secondary leading-relaxed">{summary}</p>}
      {strengths && strengths.length > 0 && (
        <div>
          <p className="font-semibold text-green-600 uppercase tracking-wide mb-1">Strengths</p>
          <ul className="list-disc list-inside text-text-secondary space-y-0.5">
            {strengths.slice(0, 3).map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ul>
        </div>
      )}
      {weaknesses && weaknesses.length > 0 && (
        <div>
          <p className="font-semibold text-red-500 uppercase tracking-wide mb-1">Weaknesses</p>
          <ul className="list-disc list-inside text-text-secondary space-y-0.5">
            {weaknesses.slice(0, 3).map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}
      {opportunities && opportunities.length > 0 && (
        <div>
          <p className="font-semibold text-brand uppercase tracking-wide mb-1">Opportunities</p>
          <ul className="list-disc list-inside text-text-secondary space-y-0.5">
            {opportunities.slice(0, 3).map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export function WidgetRenderer({
  widgetType,
  data,
}: {
  widgetType: string;
  data: Record<string, unknown>;
}) {
  switch (widgetType) {
    case "metric_card":
      return <MetricCard data={data} />;
    case "summary_card":
    case "insight_list":
      return <SummaryCard data={data} />;
    case "trend_indicator":
      return <TrendIndicator data={data} />;
    case "line_chart":
      return <LineChart data={data} />;
    case "bar_chart":
      return <BarChart data={data} />;
    case "pie_chart":
    case "donut_chart":
      return <DonutChart data={data} />;
    case "horizontal_bar_chart":
      return <HorizontalBarChart data={data} />;
    case "comparison_chart":
      return <ComparisonChart data={data} />;
    case "review_list":
      return <ReviewListWidget data={data} />;
    case "comparison_card":
      return <ComparisonWidget data={data} />;
    default:
      return (
        <p className="text-xs text-text-muted italic">
          Unsupported widget type: <span className="font-mono">{widgetType}</span>
        </p>
      );
  }
}
