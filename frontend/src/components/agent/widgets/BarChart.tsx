"use client";

type BarRow = { label: string; value: number };

function toInt(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return Math.round(value);
  if (typeof value === "string") {
    const n = Number(value);
    return Number.isFinite(n) ? Math.round(n) : 0;
  }
  return 0;
}

export function BarChart({ data }: { data: Record<string, unknown> }) {
  const raw = Array.isArray(data.bars) ? data.bars : [];
  const bars: BarRow[] = raw
    .map((row) => {
      const r = row as Record<string, unknown>;
      const label = typeof r.label === "string" ? r.label : String(r.label ?? "");
      return { label, value: toInt(r.value) };
    })
    .filter((b) => b.label.length > 0);

  if (bars.length === 0) {
    return <p className="text-xs text-text-muted">No chart data available.</p>;
  }

  const chartW = 100;
  const chartH = 44;
  const gap = 3;
  const n = bars.length;
  const slot = (chartW - gap * Math.max(0, n - 1)) / n;
  const maxVal = Math.max(...bars.map((b) => b.value), 1);

  return (
    <div className="space-y-2">
      <div className="h-32 w-full rounded-lg border border-border-subtle bg-gradient-to-b from-surface-card to-surface px-2 pt-2 pb-1">
        <svg
          viewBox={`0 0 ${chartW} ${chartH}`}
          className="h-full w-full"
          preserveAspectRatio="none"
        >
          {bars.map((b, i) => {
            const x = i * (slot + gap);
            const h = (b.value / maxVal) * (chartH - 10);
            const y = chartH - h;
            const w = Math.max(slot - 1, 0.5);
            return (
              <rect
                key={`${b.label}-${i}`}
                x={x}
                y={y}
                width={w}
                height={Math.max(h, 0)}
                rx={1}
                className="fill-brand/90"
              />
            );
          })}
        </svg>
      </div>
      <div className="flex flex-wrap justify-between gap-x-1 gap-y-0.5 text-[10px] text-text-muted leading-tight">
        {bars.map((b) => (
          <span key={b.label} className="tabular-nums">
            {b.label}: {b.value}
          </span>
        ))}
      </div>
    </div>
  );
}
