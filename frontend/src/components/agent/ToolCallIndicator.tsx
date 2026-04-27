// Exported for tests.
export const TOOL_LABELS: Record<string, string> = {
  get_dashboard: "Loading overview…",
  query_reviews: "Searching reviews…",
  run_analysis: "Running AI analysis…",
  compare_competitors: "Comparing competitors…",
  get_review_trends: "Calculating trends…",
  get_review_series: "Loading chart data…",
  get_top_issues: "Analyzing top issues…",
  pin_widget: "Pinning to workspace…",
};

export function ToolCallIndicator({ name, isStreaming }: { name: string; isStreaming: boolean }) {
  return (
    <div className="flex items-center gap-2 text-xs text-text-muted py-1 pl-1">
      {isStreaming ? (
        <span className="inline-block h-3 w-3 border border-brand border-t-transparent rounded-full animate-spin shrink-0" />
      ) : (
        <span className="text-brand shrink-0 font-medium">✓</span>
      )}
      {TOOL_LABELS[name] ?? `Calling ${name.replace(/_/g, " ")}…`}
    </div>
  );
}
