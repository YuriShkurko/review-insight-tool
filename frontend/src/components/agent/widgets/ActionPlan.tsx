type PlanItem = {
  id?: string;
  rank?: number;
  title?: string;
  issue_or_opportunity?: string;
  evidence?: string;
  likely_cause?: string;
  recommended_action?: string;
  effort?: string;
  impact?: string;
  priority?: string;
  suggested_owner?: string;
  metric_to_watch?: string;
  example_response?: string | null;
  source?: string;
  is_demo?: boolean;
};

const PRIORITY_STYLES: Record<string, string> = {
  high: "bg-danger/10 text-danger border-danger/20",
  medium: "bg-warning/10 text-warning border-warning/20",
  low: "bg-success/10 text-success border-success/20",
  critical: "bg-danger/20 text-danger border-danger/30",
};

const IMPACT_COLORS: Record<string, string> = {
  high: "text-danger",
  medium: "text-warning",
  low: "text-success",
};

function priorityChip(priority?: string): string {
  return (
    PRIORITY_STYLES[(priority ?? "").toLowerCase()] ??
    "bg-surface border-border-subtle text-text-muted"
  );
}

function impactColor(impact?: string): string {
  return IMPACT_COLORS[(impact ?? "").toLowerCase()] ?? "text-text-muted";
}

function itemTitle(item: PlanItem): string {
  return item.issue_or_opportunity ?? item.title ?? "Recommended move";
}

export function ActionPlan({
  widgetType,
  data,
}: {
  widgetType: string;
  data: Record<string, unknown>;
}) {
  const isActionPlan = widgetType === "action_plan";
  const rawItems = isActionPlan
    ? Array.isArray(data.actions)
      ? data.actions
      : []
    : Array.isArray(data.opportunities)
      ? data.opportunities
      : [];
  const items = rawItems as PlanItem[];
  const summary = typeof data.summary === "string" ? data.summary : null;
  const confidence = typeof data.confidence === "string" ? data.confidence : null;
  const isDemo = data.is_demo === true;
  const limitations = Array.isArray(data.limitations)
    ? data.limitations.filter((x) => typeof x === "string")
    : [];

  if (items.length === 0 && !summary) {
    return <p className="text-xs text-text-muted">No action data available.</p>;
  }

  return (
    <div className="space-y-2.5">
      {(summary || isDemo || confidence) && (
        <div className="flex items-start justify-between gap-3">
          {summary && <p className="text-xs leading-relaxed text-text-secondary">{summary}</p>}
          <div className="shrink-0 text-right text-[11px]">
            {isDemo && (
              <span className="rounded-full border border-warning/30 bg-warning-soft px-2 py-0.5 text-warning">
                Demo signals
              </span>
            )}
            {confidence && !isDemo && (
              <span className="text-text-muted">Confidence: {confidence}</span>
            )}
          </div>
        </div>
      )}

      <div className="space-y-2">
        {items.slice(0, 4).map((item, index) => {
          const rank = isActionPlan ? (item.rank ?? index + 1) : null;
          return (
            <div
              key={item.id ?? `${itemTitle(item)}-${index}`}
              className="rounded-xl border border-border-subtle bg-surface-card"
            >
              <div className="flex items-start gap-3 p-3">
                {rank !== null && (
                  <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-brand/10 text-[11px] font-semibold text-brand">
                    {rank}
                  </span>
                )}
                <div className="min-w-0 flex-1 space-y-1.5">
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <p className="text-xs font-semibold text-text-primary">{itemTitle(item)}</p>
                    <div className="flex flex-wrap items-center gap-1.5">
                      {item.priority && (
                        <span
                          className={`rounded-full border px-2 py-0.5 text-[10px] font-medium capitalize ${priorityChip(item.priority)}`}
                        >
                          {item.priority}
                        </span>
                      )}
                      {item.impact && (
                        <span
                          className={`text-[10px] font-medium capitalize ${impactColor(item.impact)}`}
                        >
                          {item.impact} impact
                        </span>
                      )}
                    </div>
                  </div>

                  {item.evidence && (
                    <p className="border-l-2 border-border-subtle pl-2 text-[11px] leading-relaxed text-text-muted">
                      {item.evidence}
                    </p>
                  )}

                  {item.recommended_action && (
                    <p className="text-[11px] text-text-secondary">
                      <span className="font-semibold text-brand">Do: </span>
                      {item.recommended_action}
                    </p>
                  )}

                  {(item.suggested_owner || item.metric_to_watch || item.effort) && (
                    <div className="flex flex-wrap gap-x-3 gap-y-0.5 text-[10px] text-text-muted">
                      {item.suggested_owner && <span>Owner: {item.suggested_owner}</span>}
                      {item.metric_to_watch && <span>Watch: {item.metric_to_watch}</span>}
                      {item.effort && <span>Effort: {item.effort}</span>}
                    </div>
                  )}

                  {item.example_response && (
                    <p className="rounded-lg border border-brand/20 bg-brand/5 px-2 py-1.5 text-[11px] text-text-secondary">
                      {item.example_response}
                    </p>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {limitations.length > 0 && (
        <p className="text-[11px] italic leading-relaxed text-text-muted">{limitations[0]}</p>
      )}
    </div>
  );
}
