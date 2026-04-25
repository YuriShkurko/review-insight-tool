const TOOL_LABELS: Record<string, string> = {
  get_dashboard: "Loading overview…",
  query_reviews: "Searching reviews…",
  run_analysis: "Running AI analysis…",
  compare_competitors: "Comparing competitors…",
  get_review_trends: "Calculating trends…",
  pin_widget: "Pinning to workspace…",
};

export function ToolCallIndicator({ name }: { name: string }) {
  return (
    <div className="flex items-center gap-2 text-xs text-gray-400 py-1 pl-1">
      <span className="inline-block h-3 w-3 border border-blue-400 border-t-transparent rounded-full animate-spin shrink-0" />
      {TOOL_LABELS[name] ?? `Calling ${name.replace(/_/g, " ")}…`}
    </div>
  );
}
