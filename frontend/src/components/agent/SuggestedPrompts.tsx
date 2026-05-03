const PROMPTS = [
  "How is the business doing?",
  "Show me our worst reviews this month",
  "What are our top complaints?",
  "Build a business insight dashboard",
  "What should we focus on improving?",
  "Show me our rating trend over 30 days",
  "Show me the profit bridge",
];

export function SuggestedPrompts({ onSelect }: { onSelect: (prompt: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 px-6 py-8">
      <div className="text-center">
        <div className="mx-auto mb-3 h-9 w-9 rounded-lg bg-brand-light" />
        <p className="text-lg font-semibold text-text-primary">Ask your business copilot</p>
        <p className="mt-1.5 max-w-xs text-sm leading-relaxed text-text-secondary">
          Start with reviews, spot business signals, and pin useful answers directly to the
          dashboard.
        </p>
      </div>
      <div className="grid w-full max-w-sm grid-cols-2 gap-2">
        {PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onSelect(p)}
            className="rounded-lg border border-border bg-surface-card px-3 py-2.5 text-left text-xs leading-snug text-text-secondary shadow-sm transition-all hover:-translate-y-0.5 hover:border-brand/40 hover:text-brand hover:shadow"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
