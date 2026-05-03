type SubScore = {
  id?: string;
  label?: string;
  score?: number;
  evidence?: string;
};

function asNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function scoreTone(score: number): string {
  if (score >= 75) return "text-emerald-600";
  if (score >= 55) return "text-amber-600";
  return "text-red-600";
}

export function HealthScore({ data }: { data: Record<string, unknown> }) {
  const score = asNumber(data.score);
  const label = typeof data.label === "string" ? data.label : "Business Health";
  const summary = typeof data.summary === "string" ? data.summary : null;
  const confidence = typeof data.confidence === "string" ? data.confidence : null;
  const source = typeof data.source === "string" ? data.source.replace(/_/g, " ") : null;
  const subScores = Array.isArray(data.sub_scores) ? (data.sub_scores as SubScore[]) : [];
  const drivers = Array.isArray(data.drivers)
    ? data.drivers.filter((x) => typeof x === "string")
    : [];
  const risks = Array.isArray(data.risks) ? data.risks.filter((x) => typeof x === "string") : [];
  const opportunities = Array.isArray(data.opportunities)
    ? data.opportunities.filter((x) => typeof x === "string")
    : [];
  const limitations = Array.isArray(data.limitations)
    ? data.limitations.filter((x) => typeof x === "string")
    : [];

  if (score == null) {
    return <p className="text-xs text-text-muted">No health score available.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">{label}</p>
          <p className={`mt-1 text-4xl font-semibold tracking-tight ${scoreTone(score)}`}>
            {score}
            <span className="text-base font-medium text-text-muted">/100</span>
          </p>
        </div>
        <div className="text-right text-[11px] capitalize text-text-muted">
          {confidence && <p>Confidence: {confidence}</p>}
          {source && <p>Source: {source}</p>}
        </div>
      </div>

      {summary && <p className="text-sm leading-relaxed text-text-secondary">{summary}</p>}

      {subScores.length > 0 && (
        <div className="space-y-2">
          {subScores.slice(0, 6).map((item, index) => {
            const itemScore = asNumber(item.score) ?? 0;
            return (
              <div key={item.id ?? item.label ?? index}>
                <div className="mb-1 flex items-center justify-between gap-2 text-xs">
                  <span className="font-medium text-text-secondary">{item.label ?? "Score"}</span>
                  <span className={`tabular-nums ${scoreTone(itemScore)}`}>{itemScore}</span>
                </div>
                <div className="h-1.5 rounded-full bg-surface-elevated">
                  <div
                    className="h-1.5 rounded-full bg-brand"
                    style={{ width: `${Math.max(0, Math.min(100, itemScore))}%` }}
                  />
                </div>
                {item.evidence && (
                  <p className="mt-1 line-clamp-2 text-[11px] text-text-muted">{item.evidence}</p>
                )}
              </div>
            );
          })}
        </div>
      )}

      {[drivers, risks, opportunities].some((group) => group.length > 0) && (
        <div className="grid gap-2 text-xs sm:grid-cols-3">
          {drivers.length > 0 && (
            <div className="rounded-lg border border-border-subtle p-2">
              <p className="font-semibold text-text-primary">Drivers</p>
              <p className="mt-1 text-text-muted">{drivers[0]}</p>
            </div>
          )}
          {risks.length > 0 && (
            <div className="rounded-lg border border-border-subtle p-2">
              <p className="font-semibold text-red-600">Risk</p>
              <p className="mt-1 text-text-muted">{risks[0]}</p>
            </div>
          )}
          {opportunities.length > 0 && (
            <div className="rounded-lg border border-border-subtle p-2">
              <p className="font-semibold text-brand">Opportunity</p>
              <p className="mt-1 text-text-muted">{opportunities[0]}</p>
            </div>
          )}
        </div>
      )}

      {limitations.length > 0 && (
        <p className="text-[11px] italic leading-relaxed text-text-muted">{limitations[0]}</p>
      )}
    </div>
  );
}
