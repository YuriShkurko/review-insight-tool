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
    <div className="text-center py-3">
      <p className="text-3xl font-bold text-text-primary">
        {typeof value === "number" ? value.toLocaleString() : String(value)}
      </p>
      {label && <p className="text-sm text-text-secondary mt-1">{label}</p>}
      {sublabel && <p className="text-xs text-text-muted mt-0.5">{sublabel}</p>}
    </div>
  );
}
