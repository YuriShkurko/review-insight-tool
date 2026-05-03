type Metric = {
  label?: string;
  value?: number | string;
  unit?: string;
};

function formatMetric(metric: Metric): string {
  const value =
    typeof metric.value === "number" ? metric.value.toLocaleString() : String(metric.value ?? "-");
  if (!metric.unit) return value;
  if (metric.unit === "USD") return `$${value}`;
  if (metric.unit === "%") return `${value}%`;
  return `${value} ${metric.unit}`;
}

function titleFor(widgetType: string, data: Record<string, unknown>): string {
  if (typeof data.label === "string") return data.label;
  if (widgetType === "sales_summary") return "Sales Summary";
  if (widgetType === "operations_risk") return "Operations Risk";
  if (widgetType === "local_presence_card") return "Local Presence";
  if (widgetType === "social_signal") return "Social Signals";
  return "Signal Summary";
}

export function SignalSummary({
  widgetType,
  data,
}: {
  widgetType: string;
  data: Record<string, unknown>;
}) {
  const metrics = Array.isArray(data.metrics) ? (data.metrics as Metric[]) : [];
  const items = Array.isArray(data.items) ? (data.items as Metric[]) : [];
  const summary = typeof data.summary === "string" ? data.summary : null;
  const recommendation = typeof data.recommendation === "string" ? data.recommendation : null;
  const confidence = typeof data.confidence === "string" ? data.confidence : null;
  const source = typeof data.source === "string" ? data.source.replace(/_/g, " ") : null;
  const isDemo = data.is_demo === true;
  const limitations = Array.isArray(data.limitations)
    ? data.limitations.filter((x) => typeof x === "string")
    : [];

  if (metrics.length === 0 && !summary) {
    return <p className="text-xs text-text-muted">No signal data available.</p>;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-text-muted">
            {titleFor(widgetType, data)}
          </p>
          {summary && <p className="mt-1 text-sm leading-relaxed text-text-secondary">{summary}</p>}
        </div>
        <div className="shrink-0 text-right text-[11px] capitalize text-text-muted">
          {isDemo && <p className="font-semibold text-amber-600">Demo signal</p>}
          {confidence && <p>Confidence: {confidence}</p>}
          {source && <p>Source: {source}</p>}
        </div>
      </div>

      {metrics.length > 0 && (
        <div className="grid grid-cols-3 gap-2 text-xs">
          {metrics.slice(0, 3).map((metric, index) => (
            <div
              key={`${metric.label ?? "metric"}-${index}`}
              className="rounded-lg border border-border-subtle p-2"
            >
              <p className="text-text-muted">{metric.label ?? "Metric"}</p>
              <p className="mt-1 text-base font-semibold text-text-primary">
                {formatMetric(metric)}
              </p>
            </div>
          ))}
        </div>
      )}

      {items.length > 0 && (
        <div className="space-y-1.5">
          {items.slice(0, 4).map((item, index) => (
            <div key={`${item.label ?? "item"}-${index}`}>
              <div className="mb-0.5 flex justify-between text-xs">
                <span className="text-text-secondary">{item.label ?? "Signal"}</span>
                <span className="tabular-nums text-text-primary">{formatMetric(item)}</span>
              </div>
              {typeof item.value === "number" && item.unit === "%" && (
                <div className="h-1.5 rounded-full bg-surface-elevated">
                  <div
                    className="h-1.5 rounded-full bg-brand"
                    style={{ width: `${Math.max(0, Math.min(100, item.value))}%` }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {recommendation && (
        <p className="rounded-md border border-brand/20 bg-brand/5 px-2 py-1.5 text-xs text-text-secondary">
          <span className="font-semibold text-brand">Next: </span>
          {recommendation}
        </p>
      )}

      {limitations.length > 0 && (
        <p className="text-[11px] italic leading-relaxed text-text-muted">{limitations[0]}</p>
      )}
    </div>
  );
}
