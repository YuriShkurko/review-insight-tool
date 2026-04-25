type InsightItem = { label: string; count: number };

export function SummaryCard({ data }: { data: Record<string, unknown> }) {
  const summary =
    (data.ai_summary as string | null) ??
    (data.summary as string | null) ??
    (data.comparison_summary as string | null);
  const complaints = data.top_complaints as InsightItem[] | undefined;
  const praise = data.top_praise as InsightItem[] | undefined;
  const actions = data.action_items as string[] | undefined;
  const focus = data.recommended_focus as string | null | undefined;

  return (
    <div className="space-y-3 text-sm">
      {summary && <p className="text-gray-700 leading-relaxed">{summary}</p>}
      {complaints && complaints.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-1">
            Top Complaints
          </p>
          <ul className="space-y-0.5">
            {complaints.slice(0, 4).map((item, i) => (
              <li key={i} className="text-gray-600 flex items-start gap-2 text-xs">
                <span className="shrink-0 text-gray-400 w-5 text-right">{item.count}×</span>
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      {praise && praise.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-green-600 uppercase tracking-wide mb-1">
            Top Praise
          </p>
          <ul className="space-y-0.5">
            {praise.slice(0, 4).map((item, i) => (
              <li key={i} className="text-gray-600 flex items-start gap-2 text-xs">
                <span className="shrink-0 text-gray-400 w-5 text-right">{item.count}×</span>
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      {actions && actions.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-blue-600 uppercase tracking-wide mb-1">
            Action Items
          </p>
          <ul className="list-disc list-inside space-y-0.5 text-xs text-gray-600">
            {actions.slice(0, 4).map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {focus && (
        <p className="text-xs text-gray-500 italic border-t border-gray-100 pt-2">
          Focus: {focus}
        </p>
      )}
    </div>
  );
}
