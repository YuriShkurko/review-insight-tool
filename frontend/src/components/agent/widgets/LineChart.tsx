"use client";

import { useState } from "react";

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
  const date = new Date(y, m - 1, d);
  if (Number.isNaN(date.getTime())) return dateIso;
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export function LineChart({ data }: { data: Record<string, unknown> }) {
  const [selectedIdx, setSelectedIdx] = useState<number | null>(null);
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
    return (
      <p data-testid="widget-empty-state" className="text-xs text-text-muted">
        No chart data available.
      </p>
    );
  }

  const values = points.map((p) => p.value ?? 0);
  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);

  // Smarter domain: anchor count series at zero with headroom; clamp rating to a
  // padded sub-range of [0, 5] so small movements actually read as movement.
  let yMin: number;
  let yMax: number;
  if (metric === "avg_rating") {
    yMin = Math.max(0, rawMin - 0.25);
    yMax = Math.min(5, rawMax + 0.25);
    if (yMax - yMin < 0.5) {
      const mid = (yMin + yMax) / 2;
      yMin = Math.max(0, mid - 0.25);
      yMax = Math.min(5, mid + 0.25);
    }
  } else {
    yMin = 0;
    yMax = Math.max(rawMax, 1) * 1.15;
  }
  const range = Math.max(yMax - yMin, 1e-6);

  const chartWidth = 320;
  const chartHeight = 100;
  const padX = 6;
  const padTop = 6;
  const padBottom = 6;
  const innerW = chartWidth - padX * 2;
  const innerH = chartHeight - padTop - padBottom;
  const xStep = points.length > 1 ? innerW / (points.length - 1) : innerW;

  const xy = points.map((point, index) => {
    const x = padX + index * xStep;
    const y = padTop + innerH - (((point.value ?? yMin) - yMin) / range) * innerH;
    return { x, y };
  });

  const path = xy
    .map((p, index) => `${index === 0 ? "M" : "L"} ${p.x.toFixed(2)} ${p.y.toFixed(2)}`)
    .join(" ");

  const lastPoint = points.at(-1);
  const firstPoint = points.at(0);
  const delta =
    lastPoint?.value != null && firstPoint?.value != null
      ? Number((lastPoint.value - firstPoint.value).toFixed(2))
      : null;

  // Horizontal grid: 3 lines (top, mid, bottom).
  const gridLines = [0, 0.5, 1].map((t) => padTop + innerH * t);

  // Hit zones: one transparent rect per index, snapping to the nearest point.
  const hitW = points.length > 1 ? innerW / (points.length - 1) : innerW;

  return (
    <div className="space-y-3">
      <div className="h-32 w-full rounded-lg border border-slate-200 bg-slate-50 p-3">
        <svg
          viewBox={`0 0 ${chartWidth} ${chartHeight}`}
          className="h-full w-full"
          preserveAspectRatio="xMidYMid meet"
        >
          {gridLines.map((y, i) => (
            <line
              key={`grid-${i}`}
              x1={padX}
              x2={chartWidth - padX}
              y1={y}
              y2={y}
              className="stroke-slate-200"
              strokeWidth="0.5"
            />
          ))}
          <path
            d={path}
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="chart-path-reveal text-brand"
          />
          {/* Anchor first/last so a single-point or short series still reads. */}
          {xy.length > 0 && <circle cx={xy[0].x} cy={xy[0].y} r={1.6} className="fill-brand/70" />}
          {xy.length > 1 && (
            <circle
              cx={xy[xy.length - 1].x}
              cy={xy[xy.length - 1].y}
              r={1.6}
              className="fill-brand/70"
            />
          )}
          {/* Highlighted dot for the selected index only. */}
          {selectedIdx !== null && xy[selectedIdx] && (
            <circle cx={xy[selectedIdx].x} cy={xy[selectedIdx].y} r={3} className="fill-brand" />
          )}
          {/* Invisible hit zones drive hover/click without cluttering the line. */}
          {points.map((point, index) => {
            const cx = padX + index * xStep;
            const x = Math.max(padX, cx - hitW / 2);
            const w = Math.min(hitW, chartWidth - padX - x);
            return (
              <rect
                key={`hit-${point.date}-${index}`}
                x={x}
                y={0}
                width={w}
                height={chartHeight}
                fill="transparent"
                style={{ cursor: "pointer" }}
                onMouseEnter={() => setSelectedIdx(index)}
                onMouseLeave={() => setSelectedIdx((prev) => (prev === index ? null : prev))}
                onClick={() => setSelectedIdx(selectedIdx === index ? null : index)}
              >
                <title>
                  {formatLabel(point.date)}: {point.value ?? 0}{" "}
                  {metric === "avg_rating" ? "rating" : "reviews"}
                </title>
              </rect>
            );
          })}
        </svg>
      </div>

      {selectedIdx !== null && points[selectedIdx] !== undefined && (
        <div className="flex items-center justify-between rounded-lg bg-surface-elevated px-3 py-1.5 text-xs">
          <span className="text-text-secondary">{formatLabel(points[selectedIdx].date)}</span>
          <span className="font-medium text-text-primary">
            {points[selectedIdx].value ?? 0} {metric === "avg_rating" ? "rating" : "reviews"}
          </span>
        </div>
      )}

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
