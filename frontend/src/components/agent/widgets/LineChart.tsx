type SeriesPoint = {
  date: string;
  count?: number | null;
  avg_rating?: number | null;
};

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

// Exported for unit tests.
export function formatLabel(dateIso: string): string {
  const parts = dateIso.split("-").map(Number);
  if (parts.length !== 3 || parts.some(Number.isNaN)) return dateIso;
  const [y, m, d] = parts;
  // Construct as a local date to avoid UTC-midnight → previous-day shift in UTC− zones.
  const date = new Date(y, m - 1, d);
  if (Number.isNaN(date.getTime())) return dateIso;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function LineChart({ data }: { data: Record<string, unknown> }) {
  const rawSeries = Array.isArray(data.series) ? data.series : [];
  const metric = data.metric === "avg_rating" || data.metric === "count" ? data.metric : "count";
  const points = rawSeries
    .map((row) => {
      const p = row as SeriesPoint;
      return {
        date: p.date,
        value: metric === "avg_rating" ? toNumber(p.avg_rating) : toNumber(p.count),
      };
    })
    .filter((p) => typeof p.date === "string");

  if (points.length === 0) {
    return <p className="text-xs text-text-muted">No chart data available.</p>;
  }

  const values = points.map((p) => p.value ?? 0);
  const max = Math.max(...values, 1);
  const min = Math.min(...values, 0);
  const range = Math.max(max - min, 1);

  const chartWidth = 100;
  const chartHeight = 36;
  const xStep = points.length > 1 ? chartWidth / (points.length - 1) : chartWidth;

  const path = points
    .map((point, index) => {
      const x = index * xStep;
      const y = chartHeight - (((point.value ?? 0) - min) / range) * chartHeight;
      return `${index === 0 ? "M" : "L"} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ");

  const lastPoint = points.at(-1);
  const firstPoint = points.at(0);
  const delta =
    lastPoint?.value != null && firstPoint?.value != null
      ? Number((lastPoint.value - firstPoint.value).toFixed(2))
      : null;

  return (
    <div className="space-y-3">
      <div className="h-28 w-full rounded-lg border border-border-subtle bg-gradient-to-b from-surface-card to-surface p-3">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="h-full w-full"
          preserveAspectRatio="none"
        >
          <path d={path} fill="none" stroke="currentColor" strokeWidth="2" className="text-brand" />
          {points.map((point, index) => {
            const x = index * xStep;
            const y = chartHeight - (((point.value ?? 0) - min) / range) * chartHeight;
            return (
              <circle key={`${point.date}-${index}`} cx={x} cy={y} r="1.8" className="fill-accent">
                <title>
                  {formatLabel(point.date)}: {point.value ?? 0}{" "}
                  {metric === "avg_rating" ? "rating" : "reviews"}
                </title>
              </circle>
            );
          })}
        </svg>
      </div>

      <div className="flex items-center justify-between text-xs">
        <div className="text-text-muted">
          {formatLabel(firstPoint?.date ?? "")} - {formatLabel(lastPoint?.date ?? "")}
        </div>
        {delta != null && (
          <div className={delta >= 0 ? "text-green-600" : "text-red-600"}>
            {delta >= 0 ? "+" : ""}
            {delta} {metric === "avg_rating" ? "rating" : "reviews"}
          </div>
        )}
      </div>
    </div>
  );
}
