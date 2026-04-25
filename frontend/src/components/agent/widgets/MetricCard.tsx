export function MetricCard({ data }: { data: Record<string, unknown> }) {
  const value =
    data.value ??
    (typeof data.avg_rating === "number" ? data.avg_rating : null) ??
    data.total_reviews;
  const label = data.label as string | undefined;
  const sublabel = data.sublabel as string | undefined;

  if (value === null || value === undefined) {
    return <p className="text-xs text-gray-400">No data available.</p>;
  }

  return (
    <div className="text-center py-3">
      <p className="text-3xl font-bold text-gray-900">
        {typeof value === "number" ? value.toLocaleString() : String(value)}
      </p>
      {label && <p className="text-sm text-gray-500 mt-1">{label}</p>}
      {sublabel && <p className="text-xs text-gray-400 mt-0.5">{sublabel}</p>}
    </div>
  );
}
