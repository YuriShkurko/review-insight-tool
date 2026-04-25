import { ToolCallIndicator } from "./ToolCallIndicator";
import { WidgetRenderer } from "./WidgetRenderer";
import type { MessageItem } from "@/lib/agentTypes";

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  get_dashboard: "Dashboard Overview",
  query_reviews: "Reviews",
  run_analysis: "AI Analysis",
  compare_competitors: "Competitor Comparison",
  get_review_trends: "Review Trends",
  get_review_series: "Review Trend Chart",
};

function formatToolName(name: string): string {
  return TOOL_DISPLAY_NAMES[name] ?? name.replace(/_/g, " ");
}

export function ChatMessage({
  item,
  isStreaming,
  onPin,
}: {
  item: MessageItem;
  isStreaming: boolean;
  onPin: (widgetType: string, title: string, data: Record<string, unknown>) => void;
}) {
  if (item.kind === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[80%] bg-brand text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
          {item.text}
        </div>
      </div>
    );
  }

  if (item.kind === "assistant_text") {
    if (!item.text && !isStreaming) return null;
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] text-text-primary border-l-2 border-accent/30 pl-3 py-1 text-sm leading-relaxed whitespace-pre-wrap">
          {item.text}
          {isStreaming && (
            <span className="inline-block w-0.5 h-[1em] bg-text-muted animate-pulse ml-0.5 align-text-bottom" />
          )}
        </div>
      </div>
    );
  }

  if (item.kind === "tool_call") {
    return (
      <div className="flex justify-start">
        <ToolCallIndicator name={item.name} />
      </div>
    );
  }

  if (item.kind === "tool_result") {
    if (item.name === "pin_widget") {
      return (
        <div className="flex justify-start">
          <p className="text-xs text-text-muted py-1 pl-1">Pinned to workspace</p>
        </div>
      );
    }

    const widgetType = item.widgetType ?? "summary_card";
    const title = formatToolName(item.name);
    const isChartWidget = widgetType === "line_chart" || widgetType === "bar_chart";

    return (
      <div className="flex justify-start w-full">
        <div
          className={`w-full border border-border rounded-xl overflow-hidden bg-surface-card shadow-sm ${
            isChartWidget ? "max-w-2xl" : "max-w-sm"
          }`}
        >
          <div className="px-3 py-2 bg-surface-elevated border-b border-border-subtle flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-text-secondary truncate">{title}</span>
            <button
              type="button"
              onClick={() => onPin(widgetType, title, item.result)}
              className="shrink-0 text-xs text-text-muted hover:text-brand transition-colors font-medium"
            >
              + Dashboard
            </button>
          </div>
          <div className="p-3">
            <WidgetRenderer widgetType={widgetType} data={item.result} />
          </div>
        </div>
      </div>
    );
  }

  return null;
}
