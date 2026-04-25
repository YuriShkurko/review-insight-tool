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
    <div className="flex flex-col items-center justify-center h-full px-6 py-8 gap-5">
      <div className="text-center">
        <p className="text-sm font-medium text-gray-700">Ask anything about your reviews</p>
        <p className="text-xs text-gray-400 mt-1">
          The AI can search reviews, run analysis, and pin insights to your workspace.
        </p>
      </div>
      <div className="flex flex-wrap gap-2 justify-center max-w-sm">
        {PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onSelect(p)}
            className="text-xs px-3 py-2 rounded-full border border-gray-200 bg-white text-gray-600 hover:border-blue-300 hover:text-blue-600 transition-colors"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
