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
  get_workspace: "Dashboard Widgets",
  remove_widget: "Remove Widget",
  clear_dashboard: "Clear Dashboard",
  duplicate_widget: "Copy Widget",
  set_dashboard_order: "Reorder Dashboard",
};

function formatToolName(name: string): string {
  return TOOL_DISPLAY_NAMES[name] ?? name.replace(/_/g, " ");
}

export function ChatMessage({
  item,
  isStreaming,
  isGlobalStreaming = false,
  isRecovered = false,
  onPin,
}: {
  item: MessageItem;
  isStreaming: boolean;
  isGlobalStreaming?: boolean;
  isRecovered?: boolean;
  onPin: (widgetType: string, title: string, data: Record<string, unknown>) => void;
}) {
  if (item.kind === "user") {
    return (
      <div className="flex justify-end" data-testid="chat-message" data-message-role="user">
        <div className="max-w-[80%] rounded-2xl rounded-tr-sm bg-brand px-4 py-2.5 text-sm leading-relaxed text-white shadow-sm">
          {item.text}
        </div>
      </div>
    );
  }

  if (item.kind === "assistant_text") {
    if (!item.text && !isStreaming) return null;
    return (
      <div className="flex justify-start" data-testid="chat-message" data-message-role="assistant">
        <div className="max-w-[85%] whitespace-pre-wrap rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm leading-relaxed text-text-primary shadow-sm">
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
        <div className="max-w-[85%] rounded-full border border-slate-200 bg-white px-2.5 py-1 shadow-sm">
          <ToolCallIndicator name={item.name} isStreaming={isGlobalStreaming} />
        </div>
      </div>
    );
  }

  if (item.kind === "tool_result") {
    if (item.name === "pin_widget") {
      const succeeded = item.result?.pinned === true;
      const error = (item.result?.error as string) || "Failed to pin widget";
      if (!succeeded && isRecovered) {
        return (
          <div className="flex justify-start">
            <details className="group max-w-[85%] rounded-full border border-border-subtle bg-surface px-2.5 py-1 text-xs text-text-muted">
              <summary className="cursor-pointer list-none">
                Recovered with a compatible chart type
              </summary>
              <p className="mt-1 max-w-xs whitespace-pre-wrap pl-1 text-[11px] leading-relaxed text-text-muted">
                {error}
              </p>
            </details>
          </div>
        );
      }
      return (
        <div className="flex justify-start">
          <details
            className={`max-w-[85%] rounded-full border px-2.5 py-1 text-xs shadow-sm ${
              succeeded
                ? "border-slate-200 bg-white text-text-muted"
                : "border-red-200 bg-red-50 text-red-600 dark:border-red-900 dark:bg-red-950/20"
            }`}
          >
            <summary className="cursor-pointer list-none">
              {succeeded ? "Pinned to workspace" : "Pin failed"}
            </summary>
            {!succeeded && (
              <p className="mt-1 max-w-xs whitespace-pre-wrap pl-1 text-[11px] leading-relaxed">
                {error}
              </p>
            )}
          </details>
        </div>
      );
    }

    if (
      item.name === "remove_widget" ||
      item.name === "clear_dashboard" ||
      item.name === "duplicate_widget" ||
      item.name === "set_dashboard_order"
    ) {
      const ok =
        item.result?.removed === true ||
        item.result?.cleared === true ||
        item.result?.duplicated === true ||
        item.result?.reordered === true;
      const label =
        item.name === "remove_widget"
          ? "Removed from dashboard"
          : item.name === "clear_dashboard"
            ? "Cleared dashboard"
            : item.name === "duplicate_widget"
              ? "Copied on dashboard"
              : "Dashboard order updated";
      return (
        <div className="flex justify-start">
          <details
            className={`max-w-[85%] rounded-full border px-2.5 py-1 text-xs shadow-sm ${
              ok
                ? "border-slate-200 bg-white text-text-muted"
                : "border-red-200 bg-red-50 text-red-600 dark:border-red-900 dark:bg-red-950/20"
            }`}
          >
            <summary className="cursor-pointer list-none">
              {ok ? label : `${formatToolName(item.name)} failed`}
            </summary>
            {!ok && (
              <p className="mt-1 max-w-xs whitespace-pre-wrap pl-1 text-[11px] leading-relaxed">
                {(item.result?.error as string) || "The dashboard action did not complete."}
              </p>
            )}
          </details>
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
          className={`group w-full overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm ${
            isChartWidget ? "max-w-xl" : "max-w-sm"
          }`}
        >
          <summary className="flex cursor-pointer list-none items-center justify-between gap-2 bg-slate-50 px-3 py-2">
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
                className="shrink-0 text-xs font-medium text-text-muted transition-colors hover:text-brand"
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
