"use client";

import type { Dashboard } from "@/lib/types";

function formatFreshness(isoDate: string | null): string {
  if (!isoDate) return "-";
  const diff = Date.now() - new Date(isoDate).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${Math.max(0, mins)}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatRating(value: number | null): string {
  if (value == null) return "-";
  return `${value.toFixed(1)} / 5`;
}

export function ExecutiveSummary({ dashboard }: { dashboard: Dashboard | null }) {
  if (!dashboard) return null;

  const topIssue = dashboard.top_complaints[0];
  const topPraise = dashboard.top_praise[0];
  const snapshot =
    dashboard.recommended_focus ??
    dashboard.ai_summary ??
    "Run analysis to generate a business snapshot.";

  const tiles = [
    {
      label: "Reviews",
      value: dashboard.total_reviews > 0 ? dashboard.total_reviews.toLocaleString() : "-",
      tone: "text-white",
    },
    {
      label: "Avg rating",
      value: formatRating(dashboard.avg_rating),
      tone: "text-brand",
    },
    {
      label: "Top issue",
      value: topIssue?.label ?? "-",
      tone: "text-red-300",
    },
    {
      label: "Top praise",
      value: topPraise?.label ?? "-",
      tone: "text-green-300",
    },
    {
      label: "Updated",
      value: formatFreshness(dashboard.analysis_created_at),
      tone: "text-white",
    },
  ];

  return (
    <div
      data-testid="executive-summary"
      className="shrink-0 border-b border-white/10 bg-[#111827] px-5 py-4 text-white shadow-sm"
    >
      <div className="grid gap-3 lg:grid-cols-[1.3fr_2fr]">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-white/50">
            Business snapshot
          </p>
          <p className="mt-1 line-clamp-2 text-sm font-medium leading-relaxed text-white">
            {snapshot}
          </p>
        </div>
        <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
          {tiles.map((tile) => (
            <div
              key={tile.label}
              className="min-w-0 rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2"
            >
              <p className="text-[10px] font-medium uppercase tracking-wider text-white/45">
                {tile.label}
              </p>
              <p className={`mt-1 truncate text-sm font-semibold ${tile.tone}`} title={tile.value}>
                {tile.value}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
