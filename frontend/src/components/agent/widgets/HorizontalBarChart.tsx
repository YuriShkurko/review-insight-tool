"use client";

type BarRow = { label: string; value: number; percent: number };

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

export function HorizontalBarChart({ data }: { data: Record<string, unknown> }) {
  const raw = Array.isArray(data.bars)
    ? data.bars
    : Array.isArray(data.issues)
      ? data.issues.map((issue) => ({
          label: (issue as Record<string, unknown>).theme,
          value: (issue as Record<string, unknown>).count,
        }))
      : [];
  const values = raw.map((row) => toNumber((row as Record<string, unknown>).value));
  const max = Math.max(...values, 0);
  const bars: BarRow[] = raw
    .map((row) => {
      const r = row as Record<string, unknown>;
      const value = toNumber(r.value);
      const label = typeof r.label === "string" ? r.label : String(r.label ?? "");
      return { label, value, percent: max ? Math.round((value / max) * 100) : 0 };
    })
    .filter((bar) => bar.label && bar.value > 0);

  if (!bars.length) {
    return (
      <p data-testid="widget-empty-state" className="text-xs text-text-muted">
        No chart data available.
      </p>
    );
  }

  return (
    <div className="space-y-2">
      {bars.slice(0, 8).map((bar) => (
        <div key={bar.label} className="group">
          <div className="mb-0.5 flex items-center justify-between gap-2 text-xs">
            <span className="truncate text-text-secondary">{bar.label}</span>
            <span className="tabular-nums text-text-primary">{bar.value}</span>
          </div>
          <div className="h-2 rounded-full bg-surface-elevated">
            <div
              className="h-2 rounded-full bg-brand"
              style={{ width: `${bar.percent}%` }}
              title={`${bar.label}: ${bar.value}`}
            />
          </div>
        </div>
      ))}
    </div>
  );
}
