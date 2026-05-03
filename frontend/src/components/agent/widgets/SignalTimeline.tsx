type TimelineEvent = {
  id?: string;
  date?: string;
  type?: string;
  severity?: string;
  title?: string;
  summary?: string;
  impact?: string;
};

function severityStyles(severity?: string): { dot: string; badge: string } {
  if (severity === "critical")
    return { dot: "bg-danger", badge: "text-danger bg-danger/10 border-danger/20" };
  if (severity === "warning")
    return { dot: "bg-warning", badge: "text-warning bg-warning/10 border-warning/20" };
  if (severity === "positive")
    return { dot: "bg-success", badge: "text-success bg-success/10 border-success/20" };
  return { dot: "bg-text-muted", badge: "text-text-muted bg-surface border-border-subtle" };
}

function formatDate(value?: string): string {
  if (!value) return "Recent";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleDateString("en", { month: "short", day: "numeric" });
}

export function SignalTimeline({ data }: { data: Record<string, unknown> }) {
  const events = Array.isArray(data.events) ? (data.events as TimelineEvent[]) : [];
  const period = typeof data.period === "string" ? data.period : null;
  const summary = typeof data.summary === "string" ? data.summary : null;
  const confidence = typeof data.confidence === "string" ? data.confidence : null;
  const source = typeof data.source === "string" ? data.source.replace(/_/g, " ") : null;
  const limitations = Array.isArray(data.limitations)
    ? data.limitations.filter((x) => typeof x === "string")
    : [];

  if (events.length === 0) {
    return <p className="text-xs text-text-muted">No timeline signals available.</p>;
  }

  return (
    <div className="space-y-3">
      {(summary || confidence || source) && (
        <div className="flex items-start justify-between gap-3">
          {summary && <p className="text-xs leading-relaxed text-text-secondary">{summary}</p>}
          <div className="shrink-0 text-right text-[11px] capitalize text-text-muted">
            {confidence && <p>Confidence: {confidence}</p>}
            {source && <p>{source}</p>}
          </div>
        </div>
      )}

      {period && (
        <p className="text-[11px] font-medium uppercase tracking-wide text-text-muted">{period}</p>
      )}

      <ol className="space-y-0">
        {events.slice(0, 6).map((event, index) => {
          const styles = severityStyles(event.severity);
          const isLast = index === Math.min(events.length, 6) - 1;
          return (
            <li key={event.id ?? index} className="relative flex gap-3">
              <div className="flex flex-col items-center">
                <div className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${styles.dot}`} />
                {!isLast && <div className="mt-1 w-px flex-1 bg-border-subtle" />}
              </div>
              <div className="min-w-0 flex-1 pb-3">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-[11px] tabular-nums text-text-muted">
                    {formatDate(event.date)}
                  </span>
                  {event.severity && event.severity !== "info" && (
                    <span
                      className={`rounded-full border px-1.5 py-0.5 text-[10px] font-medium capitalize ${styles.badge}`}
                    >
                      {event.severity}
                    </span>
                  )}
                </div>
                <p className="mt-0.5 text-xs font-semibold text-text-primary">
                  {event.title ?? "Signal"}
                </p>
                {event.summary && (
                  <p className="mt-0.5 text-[11px] leading-relaxed text-text-secondary">
                    {event.summary}
                  </p>
                )}
                {event.impact && (
                  <p className="mt-0.5 text-[10px] italic text-text-muted">{event.impact}</p>
                )}
              </div>
            </li>
          );
        })}
      </ol>

      {limitations.length > 0 && (
        <p className="text-[11px] italic leading-relaxed text-text-muted">{limitations[0]}</p>
      )}
    </div>
  );
}
