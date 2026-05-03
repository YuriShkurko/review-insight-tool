"use client";

import { useSortable } from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { WidgetRenderer } from "./WidgetRenderer";
import type { WorkspaceWidget } from "@/lib/agentTypes";

const FULL_WIDTH_TYPES = new Set([
  "line_chart",
  "bar_chart",
  "pie_chart",
  "donut_chart",
  "horizontal_bar_chart",
  "comparison_chart",
  "review_list",
  "summary_card",
  "insight_list",
  "comparison_card",
  "money_flow",
]);

type WidgetKind = "kpi" | "chart" | "evidence" | "recommendation" | "narrative";

const WIDGET_LABELS: Record<string, string> = {
  metric_card: "KPI",
  trend_indicator: "Trend",
  line_chart: "Time Series",
  bar_chart: "Bar Chart",
  pie_chart: "Distribution",
  donut_chart: "Distribution",
  horizontal_bar_chart: "Ranking",
  comparison_chart: "Period Comparison",
  comparison_card: "Competitor Analysis",
  health_score: "Health Score",
  signal_timeline: "Signal Timeline",
  sales_summary: "Demo · Sales",
  operations_risk: "Demo · Operations",
  local_presence_card: "Demo · Local Presence",
  social_signal: "Demo · Social",
  opportunity_list: "Opportunities",
  action_plan: "Action Plan",
  review_list: "Review Evidence",
  summary_card: "Summary",
  insight_list: "Insights",
  money_flow: "Financial Flow",
};
function widgetLabel(widgetType: string): string {
  return WIDGET_LABELS[widgetType] ?? widgetType.replace(/_/g, " ");
}

function getWidgetKind(widgetType: string): WidgetKind {
  if (widgetType === "metric_card" || widgetType === "trend_indicator") return "kpi";
  if (
    [
      "line_chart",
      "bar_chart",
      "pie_chart",
      "donut_chart",
      "horizontal_bar_chart",
      "comparison_chart",
      "comparison_card",
    ].includes(widgetType)
  ) {
    return "chart";
  }
  if (widgetType === "review_list") return "evidence";
  if (widgetType === "insight_list") return "recommendation";
  return "narrative";
}

const KIND_STYLES: Record<
  WidgetKind,
  { card: string; header: string; body: string; eyebrow: string }
> = {
  kpi: {
    card: "border-brand/20 bg-surface-card shadow-sm",
    header: "bg-brand-light/30",
    body: "px-4 py-5",
    eyebrow: "text-brand",
  },
  chart: {
    card: "border-border-subtle bg-surface-card shadow-sm",
    header: "bg-surface-card",
    body: "p-4 sm:p-5",
    eyebrow: "text-info",
  },
  evidence: {
    card: "border-border-subtle bg-surface shadow-sm",
    header: "bg-surface",
    body: "p-4",
    eyebrow: "text-text-muted",
  },
  recommendation: {
    card: "border-warning/30 bg-warning-soft shadow-sm",
    header: "bg-warning-soft",
    body: "p-4",
    eyebrow: "text-warning",
  },
  narrative: {
    card: "border-border-subtle bg-surface-card shadow-sm",
    header: "bg-surface-card",
    body: "p-4",
    eyebrow: "text-text-muted",
  },
};

export function SortableWidgetCard({
  widget,
  onDelete,
  prominence = "standard",
  readOnly = false,
}: {
  widget: WorkspaceWidget;
  onDelete: (id: string) => void;
  prominence?: "standard" | "hero";
  readOnly?: boolean;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: widget.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  };

  const isFullWidth = FULL_WIDTH_TYPES.has(widget.widget_type);
  const kind = getWidgetKind(widget.widget_type);
  const styles = KIND_STYLES[kind];
  const isHero = prominence === "hero";

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="workspace-widget"
      data-widget-id={widget.id}
      data-widget-type={widget.widget_type}
      data-widget-kind={kind}
      data-prominence={prominence}
      className={`group animate-rise-in overflow-hidden rounded-xl border transition-all duration-200 ${
        styles.card
      } ${isFullWidth || isHero ? "col-span-2" : "col-span-1"} ${
        isHero ? "xl:col-span-4 2xl:col-span-4" : ""
      } ${isDragging ? "shadow-xl ring-2 ring-brand/30" : "hover:-translate-y-0.5 hover:shadow-md"}`}
    >
      <div
        className={`flex items-center gap-2 border-b border-border-subtle px-3.5 py-2.5 ${styles.header}`}
      >
        {!readOnly && (
          <button
            type="button"
            {...attributes}
            {...listeners}
            data-testid="drag-widget-handle"
            aria-label="Drag to reorder"
            className="shrink-0 cursor-grab touch-none text-text-muted opacity-100 transition-colors hover:text-text-secondary active:cursor-grabbing lg:opacity-0 lg:group-hover:opacity-100"
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="9" cy="6" r="1.5" />
              <circle cx="15" cy="6" r="1.5" />
              <circle cx="9" cy="12" r="1.5" />
              <circle cx="15" cy="12" r="1.5" />
              <circle cx="9" cy="18" r="1.5" />
              <circle cx="15" cy="18" r="1.5" />
            </svg>
          </button>
        )}

        <div className="min-w-0 flex-1">
          <p
            data-testid="widget-title"
            className={`${isHero ? "text-base" : "text-sm"} truncate font-semibold text-text-primary`}
          >
            {widget.title}
          </p>
          <p className={`mt-0.5 text-[11px] ${styles.eyebrow}`}>
            {widgetLabel(widget.widget_type)}
          </p>
        </div>

        {!readOnly && (
          <button
            type="button"
            data-testid="remove-widget-button"
            onClick={() => onDelete(widget.id)}
            aria-label="Remove widget"
            className="shrink-0 text-lg leading-none text-text-muted opacity-100 transition-colors hover:text-red-500 lg:opacity-0 lg:group-hover:opacity-100"
          >
            x
          </button>
        )}
      </div>
      <div data-testid="widget-chart" className={`animate-chart-reveal ${styles.body}`}>
        <WidgetRenderer widgetType={widget.widget_type} data={widget.data} />
      </div>
    </div>
  );
}
