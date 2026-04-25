const PROMPTS = [
  "What are customers saying about us?",
  "Show me our worst reviews this month",
  "What are our top complaints?",
  "How do we compare to competitors?",
  "What should we focus on improving?",
  "Show me our rating trend over 30 days",
];

export function SuggestedPrompts({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 gap-6">
      <div className="text-center">
        <div className="text-4xl mb-3">✦</div>
        <p className="text-lg font-semibold text-text-primary">Ask anything about your reviews</p>
        <p className="text-sm text-text-secondary mt-1.5 leading-relaxed max-w-xs">
          The AI can search reviews, spot trends, and pin insights directly to your dashboard.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-2 w-full max-w-sm">
        {PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onSelect(p)}
            className="text-xs px-3 py-2.5 rounded-xl border border-border bg-surface-card text-text-secondary hover:border-brand/40 hover:text-brand hover:bg-brand-light/20 shadow-sm hover:shadow transition-all text-left leading-snug"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
