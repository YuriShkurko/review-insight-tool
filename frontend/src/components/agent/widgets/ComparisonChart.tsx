"use client";

type PeriodStats = { count?: number; avg_rating?: number | null };

function toNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
}

export function ComparisonChart({ data }: { data: Record<string, unknown> }) {
  const current = data.current as PeriodStats | undefined;
  const previous = data.previous as PeriodStats | undefined;
  const currentRating = toNumber(current?.avg_rating);
  const previousRating = toNumber(previous?.avg_rating);
  const currentCount = toNumber(current?.count);
  const previousCount = toNumber(previous?.count);

  if (!current || !previous || (currentRating == null && currentCount == null)) {
    return <p className="text-xs text-text-muted">No comparison data available.</p>;
  }

  const maxCount = Math.max(currentCount ?? 0, previousCount ?? 0, 1);
  const ratingDelta = toNumber(data.rating_delta);
  const countDelta = toNumber(data.count_delta);

  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 text-xs">
        <div className="rounded-lg border border-border-subtle p-2">
          <p className="text-text-muted">{String(data.current_period ?? "Current")}</p>
          <p className="text-lg font-semibold text-text-primary">
            {currentRating != null ? currentRating.toFixed(2) : "-"}
          </p>
          <p className="text-text-muted">{currentCount ?? 0} reviews</p>
        </div>
        <div className="rounded-lg border border-border-subtle p-2">
          <p className="text-text-muted">{String(data.previous_period ?? "Previous")}</p>
          <p className="text-lg font-semibold text-text-primary">
            {previousRating != null ? previousRating.toFixed(2) : "-"}
          </p>
          <p className="text-text-muted">{previousCount ?? 0} reviews</p>
        </div>
      </div>
      <div className="space-y-1.5">
        {[
          { label: "Current volume", value: currentCount ?? 0 },
          { label: "Previous volume", value: previousCount ?? 0 },
        ].map((row) => (
          <div key={row.label}>
            <div className="mb-0.5 flex justify-between text-xs">
              <span className="text-text-secondary">{row.label}</span>
              <span className="tabular-nums text-text-primary">{row.value}</span>
            </div>
            <div className="h-2 rounded-full bg-surface-elevated">
              <div
                className="h-2 rounded-full bg-accent"
                style={{ width: `${Math.round((row.value / maxCount) * 100)}%` }}
                title={`${row.label}: ${row.value}`}
              />
            </div>
          </div>
        ))}
      </div>
      {(ratingDelta != null || countDelta != null) && (
        <p className="text-xs text-text-muted">
          Delta: {ratingDelta != null ? `${ratingDelta >= 0 ? "+" : ""}${ratingDelta} rating` : ""}
          {ratingDelta != null && countDelta != null ? ", " : ""}
          {countDelta != null ? `${countDelta >= 0 ? "+" : ""}${countDelta} reviews` : ""}
        </p>
      )}
    </div>
  );
}
