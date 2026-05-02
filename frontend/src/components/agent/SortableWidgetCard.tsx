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
]);

type WidgetKind = "kpi" | "chart" | "evidence" | "recommendation" | "narrative";

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
    card: "border-brand/20 bg-white shadow-sm",
    header: "bg-brand-light/40",
    body: "px-4 py-5",
    eyebrow: "text-brand",
  },
  chart: {
    card: "border-border-subtle bg-white shadow-sm",
    header: "bg-white",
    body: "p-4 sm:p-5",
    eyebrow: "text-accent",
  },
  evidence: {
    card: "border-slate-200 bg-slate-50/80 shadow-sm",
    header: "bg-slate-50/80",
    body: "p-4",
    eyebrow: "text-slate-500",
  },
  recommendation: {
    card: "border-amber-200 bg-amber-50/60 shadow-sm",
    header: "bg-amber-50/70",
    body: "p-4",
    eyebrow: "text-amber-700",
  },
  narrative: {
    card: "border-border-subtle bg-white shadow-sm",
    header: "bg-white",
    body: "p-4",
    eyebrow: "text-text-muted",
  },
};

export function SortableWidgetCard({
  widget,
  onDelete,
  prominence = "standard",
}: {
  widget: WorkspaceWidget;
  onDelete: (id: string) => void;
  prominence?: "standard" | "hero";
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
      className={`group animate-rise-in overflow-hidden rounded-lg border transition-all duration-200 ${
        styles.card
      } ${isFullWidth || isHero ? "col-span-2" : "col-span-1"} ${
        isHero ? "xl:col-span-2 2xl:col-span-2" : ""
      } ${isDragging ? "shadow-xl ring-2 ring-brand/30" : "hover:-translate-y-0.5 hover:shadow-md"}`}
    >
      <div
        className={`flex items-center gap-2 border-b border-border-subtle px-3.5 py-2.5 ${styles.header}`}
      >
        <button
          type="button"
          {...attributes}
          {...listeners}
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

        <div className="min-w-0 flex-1">
          <p
            data-testid="widget-title"
            className={`${isHero ? "text-base" : "text-sm"} truncate font-semibold text-text-primary`}
          >
            {widget.title}
          </p>
          <p className={`mt-0.5 text-[11px] capitalize ${styles.eyebrow}`}>
            {widget.widget_type.replace(/_/g, " ")}
          </p>
        </div>

        <button
          type="button"
          data-testid="remove-widget-button"
          onClick={() => onDelete(widget.id)}
          aria-label="Remove widget"
          className="shrink-0 text-lg leading-none text-text-muted opacity-100 transition-colors hover:text-red-500 lg:opacity-0 lg:group-hover:opacity-100"
        >
          x
        </button>
      </div>
      <div data-testid="widget-chart" className={styles.body}>
        <WidgetRenderer widgetType={widget.widget_type} data={widget.data} />
      </div>
    </div>
  );
}
