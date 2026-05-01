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
  get_rating_distribution: "Rating Distribution",
  get_top_issues: "Top Issues",
  get_review_insights: "Review Insights",
  get_review_change_summary: "Period Comparison",
};

function formatToolName(name: string): string {
  return TOOL_DISPLAY_NAMES[name] ?? name.replace(/_/g, " ");
}

export function ChatMessage({
  item,
  isStreaming,
  isGlobalStreaming = false,
  onPin,
}: {
  item: MessageItem;
  isStreaming: boolean;
  isGlobalStreaming?: boolean;
  onPin: (widgetType: string, title: string, data: Record<string, unknown>) => void;
}) {
  if (item.kind === "user") {
    return (
      <div className="flex justify-end" data-testid="chat-message" data-message-role="user">
        <div className="max-w-[80%] bg-brand text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
          {item.text}
        </div>
      </div>
    );
  }

  if (item.kind === "assistant_text") {
    if (!item.text && !isStreaming) return null;
    return (
      <div className="flex justify-start" data-testid="chat-message" data-message-role="assistant">
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
        <div className="max-w-[85%] rounded-full border border-border-subtle bg-surface px-2.5 py-1">
          <ToolCallIndicator name={item.name} isStreaming={isGlobalStreaming} />
        </div>
      </div>
    );
  }

  if (item.kind === "tool_result") {
    if (item.name === "pin_widget") {
      const succeeded = item.result?.pinned === true;
      return (
        <div className="flex justify-start">
          <p className={`text-xs py-1 pl-1 ${succeeded ? "text-text-muted" : "text-red-500"}`}>
            {succeeded
              ? "Pinned to workspace"
              : (item.result?.error as string) || "Failed to pin widget"}
          </p>
        </div>
      );
    }

    const widgetType = item.widgetType ?? "summary_card";
    const title = formatToolName(item.name);
    const isChartWidget = [
      "line_chart",
      "bar_chart",
      "pie_chart",
      "donut_chart",
      "horizontal_bar_chart",
      "comparison_chart",
    ].includes(widgetType);

    return (
      <div className="flex w-full justify-start" data-testid="chat-tool-result">
        <details
          className={`group w-full overflow-hidden rounded-lg border border-border bg-surface-card shadow-sm ${
            isChartWidget ? "max-w-xl" : "max-w-sm"
          }`}
        >
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 bg-surface-elevated px-3 py-2">
            <span className="min-w-0 truncate text-xs font-medium text-text-secondary">
              {title} preview
            </span>
            <span className="shrink-0 text-[10px] text-text-muted group-open:hidden">Expand</span>
            <span className="hidden shrink-0 text-[10px] text-text-muted group-open:inline">
              Collapse
            </span>
          </summary>
          <div className="border-t border-border-subtle px-3 py-2">
            <div className="mb-2 flex items-center justify-between gap-2">
              <span className="truncate text-xs text-text-muted">
                {widgetType.replace(/_/g, " ")}
              </span>
              <button
                type="button"
                data-testid="pin-widget-button"
                onClick={() => onPin(widgetType, title, item.result)}
                className="shrink-0 text-xs text-text-muted hover:text-brand transition-colors font-medium"
              >
                + Dashboard
              </button>
            </div>
            <WidgetRenderer widgetType={widgetType} data={item.result} />
          </div>
        </details>
      </div>
    );
  }

  return null;
}
