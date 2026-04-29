"use client";

import { useState } from "react";

type Slice = { label: string; value: number; percent?: number };

const COLORS = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#7c3aed", "#0891b2"];

function toNumber(value: unknown): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string") {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }
  return 0;
}

function normalizeSlices(data: Record<string, unknown>): Slice[] {
  const raw = Array.isArray(data.slices) ? data.slices : Array.isArray(data.bars) ? data.bars : [];
  const total = raw.reduce((sum, row) => sum + toNumber((row as Record<string, unknown>).value), 0);
  return raw
    .map((row) => {
      const r = row as Record<string, unknown>;
      const value = toNumber(r.value);
      const label = typeof r.label === "string" ? r.label : String(r.label ?? "");
      const percent =
        toNumber(r.percent) || (total ? Number(((value / total) * 100).toFixed(1)) : 0);
      return { label, value, percent };
    })
    .filter((slice) => slice.label && slice.value > 0);
}

function arcPath(cx: number, cy: number, r: number, start: number, end: number): string {
  const startX = cx + r * Math.cos(start);
  const startY = cy + r * Math.sin(start);
  const endX = cx + r * Math.cos(end);
  const endY = cy + r * Math.sin(end);
  const large = end - start > Math.PI ? 1 : 0;
  return `M ${cx} ${cy} L ${startX} ${startY} A ${r} ${r} 0 ${large} 1 ${endX} ${endY} Z`;
}

export function DonutChart({ data }: { data: Record<string, unknown> }) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
  const slices = normalizeSlices(data);
  const total = slices.reduce((sum, slice) => sum + slice.value, 0);

  if (!slices.length || total <= 0) {
    return <p className="text-xs text-text-muted">No chart data available.</p>;
  }

  const segments = slices.reduce<Array<{ slice: Slice; path: string }>>((acc, slice) => {
    const start = acc.length
      ? -Math.PI / 2 +
        slices
          .slice(0, acc.length)
          .reduce((sum, prior) => sum + (prior.value / total) * Math.PI * 2, 0)
      : -Math.PI / 2;
    const end = start + (slice.value / total) * Math.PI * 2;
    return [...acc, { slice, path: arcPath(50, 50, 44, start, end) }];
  }, []);

  return (
    <div className="grid grid-cols-[88px_1fr] items-center gap-3">
      <svg viewBox="0 0 100 100" className="h-24 w-24" role="img" aria-label="Donut chart">
        {segments.map(({ slice, path }, index) => {
          const isSelected = selectedIdx === index;
          return (
            <path
              key={slice.label}
              d={path}
              fill={COLORS[index % COLORS.length]}
              opacity={selectedIdx !== null && !isSelected ? 0.45 : 1}
              stroke={isSelected ? "white" : "none"}
              strokeWidth={isSelected ? 2 : 0}
              style={{ cursor: "pointer" }}
              onClick={() => setSelectedIdx(isSelected ? null : index)}
            >
              <title>{`${slice.label}: ${slice.value} (${slice.percent}%)`}</title>
            </path>
          );
        })}
        <circle cx="50" cy="50" r="25" className="fill-surface-card" />
        <text x="50" y="53" textAnchor="middle" className="fill-text-primary text-[13px] font-bold">
          {selectedIdx !== null && slices[selectedIdx] !== undefined
            ? slices[selectedIdx].value
            : total}
        </text>
      </svg>
      <div className="space-y-1 text-xs">
        {slices.map((slice, index) => {
          const isSelected = selectedIdx === index;
          return (
            <div
              key={slice.label}
              className={`flex cursor-pointer items-center justify-between gap-2 rounded transition-colors ${isSelected ? "bg-surface-elevated" : ""}`}
              onClick={() => setSelectedIdx(isSelected ? null : index)}
            >
              <span
                className={`flex min-w-0 items-center gap-1.5 ${isSelected ? "text-text-primary font-medium" : "text-text-secondary"}`}
              >
                <span
                  className="h-2 w-2 shrink-0 rounded-sm"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="truncate">{slice.label}</span>
              </span>
              <span
                className={`shrink-0 tabular-nums ${isSelected ? "text-text-primary font-medium" : "text-text-primary"}`}
              >
                {slice.value} ({slice.percent}%)
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
