export function MetricCard({ data }: { data: Record<string, unknown> }) {
  const value =
    data.value ??
    (typeof data.avg_rating === "number" ? data.avg_rating : null) ??
    data.total_reviews;
  const label = data.label as string | undefined;
  const sublabel = data.sublabel as string | undefined;

  if (value === null || value === undefined) {
    return (
      <p data-testid="widget-empty-state" className="text-xs text-text-muted">
        No data available.
      </p>
    );
  }

  return (
    <div className="py-3 text-left">
      <p className="text-4xl font-semibold tracking-tight text-text-primary">
        {typeof value === "number" ? value.toLocaleString() : String(value)}
      </p>
      {label && <p className="mt-1 text-sm font-medium text-text-secondary">{label}</p>}
      {sublabel && <p className="mt-0.5 text-xs text-text-muted">{sublabel}</p>}
    </div>
  );
}
