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

type PeriodStats = { count?: number; avg_rating?: number | null };
type ThemeRow = { theme?: string; count?: number; avg_rating?: number | null };

function formatRating(value: unknown): string {
  if (typeof value === "number" && Number.isFinite(value)) return value.toFixed(2);
  return "-";
}

function ComparisonWidget({ data }: { data: Record<string, unknown> }) {
  const summary =
    (data.comparison_summary as string | null | undefined) ??
    (data.summary as string | null | undefined);
  const strengths = data.strengths as string[] | undefined;
  const weaknesses = data.weaknesses as string[] | undefined;
  const opportunities = data.opportunities as string[] | undefined;

  const current = data.current as PeriodStats | undefined;
  const previous = data.previous as PeriodStats | undefined;
  const currentLabel = (data.current_period as string | undefined) ?? "Current";
  const previousLabel = (data.previous_period as string | undefined) ?? "Previous";
  const ratingDelta = data.rating_delta as number | null | undefined;
  const countDelta = data.count_delta as number | null | undefined;
  const currentThemes = (data.current_themes as ThemeRow[] | undefined) ?? [];
  const previousThemes = (data.previous_themes as ThemeRow[] | undefined) ?? [];
  const limitation = data.limitation as string | null | undefined;
  const recommended = data.recommended_focus as string | null | undefined;

  const hasPeriodStats = !!(current || previous);
  const hasNarrative =
    !!summary ||
    (strengths && strengths.length > 0) ||
    (weaknesses && weaknesses.length > 0) ||
    (opportunities && opportunities.length > 0);

  if (!hasPeriodStats && !hasNarrative && !recommended && !limitation) {
    return <p className="text-xs text-text-muted">No comparison data available.</p>;
  }

  return (
    <div className="space-y-3 text-xs">
      {summary && <p className="text-text-secondary leading-relaxed">{summary}</p>}

      {hasPeriodStats && (
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-border-subtle p-2">
            <p className="text-text-muted">{currentLabel}</p>
            <p className="text-lg font-semibold text-text-primary">
              {formatRating(current?.avg_rating)}
            </p>
            <p className="text-text-muted">{current?.count ?? 0} reviews</p>
          </div>
          <div className="rounded-lg border border-border-subtle p-2">
            <p className="text-text-muted">{previousLabel}</p>
            <p className="text-lg font-semibold text-text-primary">
              {formatRating(previous?.avg_rating)}
            </p>
            <p className="text-text-muted">{previous?.count ?? 0} reviews</p>
          </div>
        </div>
      )}

      {(typeof ratingDelta === "number" || typeof countDelta === "number") && (
        <p className="text-text-muted">
          Delta:{" "}
          {typeof ratingDelta === "number"
            ? `${ratingDelta >= 0 ? "+" : ""}${ratingDelta} rating`
            : ""}
          {typeof ratingDelta === "number" && typeof countDelta === "number" ? ", " : ""}
          {typeof countDelta === "number"
            ? `${countDelta >= 0 ? "+" : ""}${countDelta} reviews`
            : ""}
        </p>
      )}

      {currentThemes.length > 0 && (
        <div>
          <p className="font-semibold text-text-secondary uppercase tracking-wide mb-1">
            Top themes — {currentLabel}
          </p>
          <ul className="list-disc list-inside text-text-secondary space-y-0.5">
            {currentThemes.slice(0, 3).map((t, i) => (
              <li key={`c-${i}`}>
                {t.theme ?? "Theme"}
                {typeof t.count === "number" ? ` — ${t.count} mentions` : ""}
                {typeof t.avg_rating === "number" ? ` (${t.avg_rating.toFixed(2)})` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

      {previousThemes.length > 0 && (
        <div>
          <p className="font-semibold text-text-muted uppercase tracking-wide mb-1">
            Top themes — {previousLabel}
          </p>
          <ul className="list-disc list-inside text-text-muted space-y-0.5">
            {previousThemes.slice(0, 3).map((t, i) => (
              <li key={`p-${i}`}>
                {t.theme ?? "Theme"}
                {typeof t.count === "number" ? ` — ${t.count} mentions` : ""}
              </li>
            ))}
          </ul>
        </div>
      )}

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

      {recommended && (
        <p className="rounded-md border border-brand/20 bg-brand/5 px-2 py-1.5 text-text-secondary">
          <span className="font-semibold text-brand">Focus: </span>
          {recommended}
        </p>
      )}
      {limitation && <p className="italic text-text-muted">{limitation}</p>}
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
