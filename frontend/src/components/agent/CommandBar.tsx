"use client";

const AGENT_COMMANDS = [
  {
    id: "build-demo-dashboard",
    label: "Build demo dashboard",
    prompt:
      "Build a concise demo dashboard with the strongest rating, trend, issue, evidence, and action widgets. Clear stale clutter first if needed.",
  },
  {
    id: "show-top-issues",
    label: "Show top issues",
    prompt: "Show the top customer issues and pin the most useful result to the dashboard.",
  },
  {
    id: "show-positives",
    label: "Show positives",
    prompt:
      "Show what customers praise most. Use get_review_insights with focus='positive' and period='past_30d', then pin exactly one widget using source_tool='get_review_insights' and widget_type='summary_card' (or 'insight_list' if that better fits the returned themes). If data is sparse, pin one honest summary_card with the limitation. Do not add more than one widget.",
  },
  {
    id: "compare-last-30-days",
    label: "Compare 30 days",
    prompt: "Compare recent customer sentiment over the last 30 days and pin the best comparison.",
  },
  {
    id: "clear-and-rebuild",
    label: "Clear and rebuild",
    prompt:
      "Clear the current dashboard, then rebuild a clean demo-ready dashboard with the most important widgets.",
  },
] as const;

export function CommandBar({
  isStreaming,
  canCleanLayout,
  onSendPrompt,
  onCleanLayout,
  onTogglePresentationMode,
}: {
  isStreaming: boolean;
  canCleanLayout: boolean;
  onSendPrompt: (prompt: string) => void;
  onCleanLayout: () => void;
  onTogglePresentationMode: () => void;
}) {
  return (
    <div
      data-testid="command-bar"
      className="animate-rise-in shrink-0 border-b border-white/10 bg-[#111827] px-4 py-2 text-white"
    >
      <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
        <span className="shrink-0 text-[10px] font-semibold uppercase tracking-widest text-white/35">
          Quick actions
        </span>
        {AGENT_COMMANDS.map((command) => (
          <button
            key={command.id}
            type="button"
            data-testid={`command-${command.id}`}
            disabled={isStreaming}
            onClick={() => onSendPrompt(command.prompt)}
            className="shrink-0 rounded-full border border-white/10 bg-white/[0.06] px-3 py-1.5 text-xs font-medium text-white/75 transition-colors hover:bg-white/[0.1] hover:text-white disabled:opacity-45"
          >
            {command.label}
          </button>
        ))}
        <button
          type="button"
          data-testid="command-clean-layout"
          disabled={!canCleanLayout}
          onClick={onCleanLayout}
          className="shrink-0 rounded-full border border-brand/25 bg-brand/15 px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-brand/25 disabled:opacity-45"
        >
          Clean Layout
        </button>
        <button
          type="button"
          data-testid="command-presentation-mode"
          onClick={onTogglePresentationMode}
          className="shrink-0 rounded-full border border-amber-300/25 bg-amber-300/15 px-3 py-1.5 text-xs font-medium text-amber-100 transition-colors hover:bg-amber-300/25"
        >
          Present
        </button>
      </div>
    </div>
  );
}
