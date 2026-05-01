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

export function SortableWidgetCard({
  widget,
  onDelete,
}: {
  widget: WorkspaceWidget;
  onDelete: (id: string) => void;
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

  return (
    <div
      ref={setNodeRef}
      style={style}
      data-testid="workspace-widget"
      data-widget-id={widget.id}
      data-widget-type={widget.widget_type}
      className={`bg-surface-card border border-border rounded-xl overflow-hidden shadow-sm hover:shadow-md transition-shadow ${
        isFullWidth ? "col-span-2" : "col-span-1"
      } ${isDragging ? "shadow-xl ring-2 ring-brand/20" : ""}`}
    >
      <div className="px-3 py-2 bg-surface-elevated border-b border-border-subtle flex items-center gap-2">
        {/* Drag handle */}
        <button
          type="button"
          {...attributes}
          {...listeners}
          aria-label="Drag to reorder"
          className="shrink-0 text-text-muted hover:text-text-secondary transition-colors cursor-grab active:cursor-grabbing touch-none"
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

        <div className="flex-1 min-w-0">
          <p data-testid="widget-title" className="text-sm font-medium text-text-primary truncate">
            {widget.title}
          </p>
          <p className="text-xs text-text-muted capitalize">
            {widget.widget_type.replace(/_/g, " ")}
          </p>
        </div>

        <button
          type="button"
          data-testid="remove-widget-button"
          onClick={() => onDelete(widget.id)}
          aria-label="Remove widget"
          className="shrink-0 text-text-muted hover:text-red-500 transition-colors text-lg leading-none"
        >
          ×
        </button>
      </div>
      <div data-testid="widget-chart" className="p-3">
        <WidgetRenderer widgetType={widget.widget_type} data={widget.data} />
      </div>
    </div>
  );
}
