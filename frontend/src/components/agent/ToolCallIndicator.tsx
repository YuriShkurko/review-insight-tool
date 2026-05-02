// Exported for tests.
export const TOOL_LABELS: Record<string, string> = {
  get_dashboard: "Loading overview...",
  query_reviews: "Searching reviews...",
  run_analysis: "Running AI analysis...",
  compare_competitors: "Comparing competitors...",
  get_review_trends: "Calculating trends...",
  get_review_series: "Loading chart data...",
  get_rating_distribution: "Building distribution...",
  get_top_issues: "Analyzing top issues...",
  get_review_insights: "Summarizing reviews...",
  get_review_change_summary: "Comparing periods...",
  pin_widget: "Pinning to workspace...",
  get_workspace: "Reading dashboard...",
  remove_widget: "Removing widget...",
  clear_dashboard: "Clearing dashboard...",
  duplicate_widget: "Copying widget...",
  set_dashboard_order: "Reordering dashboard...",
};

export function ToolCallIndicator({ name, isStreaming }: { name: string; isStreaming: boolean }) {
  return (
    <div className="flex items-center gap-2 py-0.5 text-xs text-text-muted">
      {isStreaming ? (
        <span className="inline-block h-3 w-3 shrink-0 animate-spin rounded-full border border-brand border-t-transparent" />
      ) : (
        <span className="shrink-0 font-medium text-brand">✓</span>
      )}
      {TOOL_LABELS[name] ?? `Calling ${name.replace(/_/g, " ")}...`}
    </div>
  );
}
