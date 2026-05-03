"use client";

import { useState } from "react";
import { chartColor } from "@/lib/chartColors";

type Slice = { label: string; value: number; percent?: number };

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
    return (
      <p data-testid="widget-empty-state" className="text-xs text-text-muted">
        No chart data available.
      </p>
    );
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

  const centerLabel =
    selectedIdx !== null && slices[selectedIdx] !== undefined
      ? `${slices[selectedIdx].percent}%`
      : String(total);
  const centerSub =
    selectedIdx !== null && slices[selectedIdx] !== undefined ? slices[selectedIdx].label : "total";

  return (
    <div className="grid grid-cols-[96px_1fr] items-center gap-4">
      <svg viewBox="0 0 100 100" className="h-24 w-24" role="img" aria-label="Donut chart">
        {segments.map(({ slice, path }, index) => {
          const isSelected = selectedIdx === index;
          const color = chartColor(index);
          return (
            <path
              key={slice.label}
              d={path}
              fill={color}
              opacity={selectedIdx !== null && !isSelected ? 0.35 : 1}
              stroke={isSelected ? "white" : "transparent"}
              strokeWidth={isSelected ? 1.5 : 0}
              style={{ cursor: "pointer" }}
              onClick={() => setSelectedIdx(isSelected ? null : index)}
            >
              <title>{`${slice.label}: ${slice.value} (${slice.percent}%)`}</title>
            </path>
          );
        })}
        <circle cx="50" cy="50" r="26" fill="white" />
        <text x="50" y="48" textAnchor="middle" fontSize="14" fontWeight="700" fill="#1c1917">
          {centerLabel}
        </text>
        <text x="50" y="60" textAnchor="middle" fontSize="7" fill="#a8a29e">
          {centerSub.length > 10 ? centerSub.slice(0, 9) + "…" : centerSub}
        </text>
      </svg>
      <div className="space-y-1.5 text-xs">
        {slices.map((slice, index) => {
          const isSelected = selectedIdx === index;
          const color = chartColor(index);
          return (
            <div
              key={slice.label}
              className={`flex cursor-pointer items-center justify-between gap-2 rounded px-1 py-0.5 transition-colors ${isSelected ? "bg-surface-elevated" : ""}`}
              onClick={() => setSelectedIdx(isSelected ? null : index)}
            >
              <span className="flex min-w-0 items-center gap-1.5">
                <span
                  className="h-2.5 w-2.5 shrink-0 rounded-sm"
                  style={{ backgroundColor: color }}
                />
                <span
                  className={`truncate ${isSelected ? "font-medium text-text-primary" : "text-text-secondary"}`}
                >
                  {slice.label}
                </span>
              </span>
              <span className="shrink-0 tabular-nums text-text-primary">
                {slice.value}
                <span className="ml-1 text-text-muted">({slice.percent}%)</span>
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
