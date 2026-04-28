type InsightItem = { label: string; count: number };

type TopIssueRow = {
  theme: string;
  count: number;
  severity?: string;
  representative_quote?: string | null;
};

export function SummaryCard({ data }: { data: Record<string, unknown> }) {
  const summary =
    (data.ai_summary as string | null) ??
    (data.summary as string | null) ??
    (data.comparison_summary as string | null);
  const complaints = data.top_complaints as InsightItem[] | undefined;
  const praise = data.top_praise as InsightItem[] | undefined;
  const actions = data.action_items as string[] | undefined;
  const focus = data.recommended_focus as string | null | undefined;
  const issues = data.issues as TopIssueRow[] | undefined;
  const period = data.period as string | undefined;

  const hasContent =
    summary ||
    (issues && issues.length > 0) ||
    (complaints && complaints.length > 0) ||
    (praise && praise.length > 0) ||
    (actions && actions.length > 0) ||
    focus;

  if (!hasContent) {
    return <p className="text-xs text-text-muted">No summary data available.</p>;
  }

  return (
    <div className="space-y-3 text-sm">
      {summary && <p className="text-text-secondary leading-relaxed">{summary}</p>}
      {issues && issues.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-text-primary uppercase tracking-wide mb-1">
            Top issues{period ? ` (${period})` : ""}
          </p>
          <ul className="space-y-2">
            {issues.slice(0, 6).map((issue, i) => (
              <li
                key={i}
                className="text-xs text-text-secondary border-b border-border-subtle last:border-0 pb-2 last:pb-0"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium text-text-primary">{issue.theme}</span>
                  <span className="shrink-0 text-text-muted tabular-nums">{issue.count}×</span>
                </div>
                {issue.severity && (
                  <p className="text-[10px] uppercase text-text-muted mt-0.5">{issue.severity}</p>
                )}
                {issue.representative_quote && (
                  <p className="text-text-muted mt-1 line-clamp-2 italic">
                    {`"${issue.representative_quote}"`}
                  </p>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {complaints && complaints.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-red-500 uppercase tracking-wide mb-1">
            Top Complaints
          </p>
          <ul className="space-y-0.5">
            {complaints.slice(0, 4).map((item, i) => (
              <li key={i} className="text-text-secondary flex items-start gap-2 text-xs">
                <span className="shrink-0 text-text-muted w-5 text-right">{item.count}×</span>
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
              <li key={i} className="text-text-secondary flex items-start gap-2 text-xs">
                <span className="shrink-0 text-text-muted w-5 text-right">{item.count}×</span>
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      {actions && actions.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-brand uppercase tracking-wide mb-1">
            Action Items
          </p>
          <ul className="list-disc list-inside space-y-0.5 text-xs text-text-secondary">
            {actions.slice(0, 4).map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {focus && (
        <p className="text-xs text-text-muted italic border-t border-border-subtle pt-2">
          Focus: {focus}
        </p>
      )}
    </div>
  );
}
