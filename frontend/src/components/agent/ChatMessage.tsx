import { ToolCallIndicator } from "./ToolCallIndicator";
import { WidgetRenderer } from "./WidgetRenderer";
import type { MessageItem } from "@/lib/agentTypes";

const TOOL_DISPLAY_NAMES: Record<string, string> = {
  get_dashboard: "Dashboard Overview",
  query_reviews: "Reviews",
  run_analysis: "AI Analysis",
  compare_competitors: "Competitor Comparison",
  get_review_trends: "Review Trends",
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
        <div className="max-w-[80%] bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm leading-relaxed">
          {item.text}
        </div>
      </div>
    );
  }

  if (item.kind === "assistant_text") {
    if (!item.text && !isStreaming) return null;
    return (
      <div className="flex justify-start">
        <div className="max-w-[85%] text-gray-900 px-1 py-1 text-sm leading-relaxed whitespace-pre-wrap">
          {item.text}
          {isStreaming && (
            <span className="inline-block w-0.5 h-[1em] bg-gray-400 animate-pulse ml-0.5 align-text-bottom" />
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
          <p className="text-xs text-gray-400 py-1 pl-1">Pinned to workspace</p>
        </div>
      );
    }

    const widgetType = item.widgetType ?? "summary_card";
    const title = formatToolName(item.name);

    return (
      <div className="flex justify-start w-full">
        <div className="w-full max-w-sm border border-gray-200 rounded-xl overflow-hidden bg-white shadow-sm">
          <div className="px-3 py-2 bg-gray-50 border-b border-gray-100 flex items-center justify-between gap-2">
            <span className="text-xs font-medium text-gray-500 truncate">{title}</span>
            <button
              type="button"
              onClick={() => onPin(widgetType, title, item.result)}
              className="shrink-0 text-xs text-gray-400 hover:text-blue-600 transition-colors"
            >
              Pin
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
