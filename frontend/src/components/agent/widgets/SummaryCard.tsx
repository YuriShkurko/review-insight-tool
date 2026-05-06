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
    (data.comparison_summary as string | null) ??
    (data.source_summary as string | null);
  const complaints = data.top_complaints as InsightItem[] | undefined;
  const praise = data.top_praise as InsightItem[] | undefined;
  const actions = data.action_items as string[] | undefined;
  const focus = data.recommended_focus as string | null | undefined;
  const issues = (data.issues ?? data.items) as TopIssueRow[] | undefined;
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
      {summary && <p className="leading-relaxed text-text-secondary">{summary}</p>}
      {issues && issues.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-text-primary">
            Top issues{period ? ` (${period})` : ""}
          </p>
          <ul className="space-y-2">
            {issues.slice(0, 6).map((issue, i) => (
              <li
                key={i}
                className="border-b border-border-subtle pb-2 text-xs text-text-secondary last:border-0 last:pb-0"
              >
                <div className="flex items-start justify-between gap-2">
                  <span className="font-medium text-text-primary">{issue.theme}</span>
                  <span className="shrink-0 tabular-nums text-text-muted">{issue.count}x</span>
                </div>
                {issue.severity && (
                  <p className="mt-0.5 text-[10px] uppercase text-text-muted">{issue.severity}</p>
                )}
                {issue.representative_quote && (
                  <p className="mt-1 line-clamp-2 text-text-muted italic">
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
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-danger">
            Top Complaints
          </p>
          <ul className="space-y-0.5">
            {complaints.slice(0, 4).map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="w-5 shrink-0 text-right text-text-muted">{item.count}x</span>
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      {praise && praise.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-success">
            Top Praise
          </p>
          <ul className="space-y-0.5">
            {praise.slice(0, 4).map((item, i) => (
              <li key={i} className="flex items-start gap-2 text-xs text-text-secondary">
                <span className="w-5 shrink-0 text-right text-text-muted">{item.count}x</span>
                {item.label}
              </li>
            ))}
          </ul>
        </div>
      )}
      {actions && actions.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-semibold uppercase tracking-wide text-brand">
            Action Items
          </p>
          <ul className="list-inside list-disc space-y-0.5 text-xs text-text-secondary">
            {actions.slice(0, 4).map((item, i) => (
              <li key={i}>{item}</li>
            ))}
          </ul>
        </div>
      )}
      {focus && (
        <p className="border-t border-border-subtle pt-2 text-xs italic text-text-muted">
          Focus: {focus}
        </p>
      )}
    </div>
  );
}
