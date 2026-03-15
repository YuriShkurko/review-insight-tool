"use client";

import type { ComparisonResponse, BusinessSnapshot } from "@/lib/types";

function SnapshotCard({
  snapshot,
  isTarget,
}: {
  snapshot: BusinessSnapshot;
  isTarget: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-5 ${
        isTarget
          ? "border-blue-200 bg-blue-50/40 ring-1 ring-blue-100"
          : "border-gray-200 bg-white"
      }`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <h4 className="font-semibold text-sm truncate">{snapshot.name}</h4>
        {isTarget && (
          <span className="text-[10px] font-semibold bg-blue-600 text-white px-2 py-0.5 rounded-full uppercase tracking-wide shrink-0">
            You
          </span>
        )}
        {snapshot.business_type && snapshot.business_type !== "other" && (
          <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full capitalize shrink-0">
            {snapshot.business_type}
          </span>
        )}
      </div>

      {/* Stats row */}
      <div className="flex items-center gap-4 text-sm mb-3">
        <span className="font-semibold text-gray-900">
          {snapshot.avg_rating != null
            ? `★ ${snapshot.avg_rating.toFixed(1)}`
            : "—"}
        </span>
        <span className="text-gray-400 text-xs">
          {snapshot.total_reviews} review{snapshot.total_reviews !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Summary */}
      <p className="text-sm text-gray-600 leading-relaxed line-clamp-3 mb-3">
        {snapshot.summary}
      </p>

      {/* Complaints & Praise compact */}
      {(snapshot.top_complaints.length > 0 || snapshot.top_praise.length > 0) && (
        <div className="pt-3 border-t border-gray-200/60 space-y-2">
          {snapshot.top_complaints.length > 0 && (
            <div className="flex items-start gap-2 text-xs">
              <span className="text-red-400 shrink-0 mt-px">&#x25CF;</span>
              <span className="text-gray-600">
                {snapshot.top_complaints.slice(0, 3).map((c) => c.label).join(" · ")}
              </span>
            </div>
          )}
          {snapshot.top_praise.length > 0 && (
            <div className="flex items-start gap-2 text-xs">
              <span className="text-green-400 shrink-0 mt-px">&#x25CF;</span>
              <span className="text-gray-600">
                {snapshot.top_praise.slice(0, 3).map((p) => p.label).join(" · ")}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function InsightColumn({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: "green" | "red" | "blue";
}) {
  if (items.length === 0) return null;
  const styles = {
    green: {
      bg: "bg-green-50/50",
      border: "border-green-200",
      dot: "text-green-500",
      heading: "text-green-700",
    },
    red: {
      bg: "bg-red-50/50",
      border: "border-red-200",
      dot: "text-red-500",
      heading: "text-red-700",
    },
    blue: {
      bg: "bg-blue-50/50",
      border: "border-blue-200",
      dot: "text-blue-500",
      heading: "text-blue-700",
    },
  };
  const s = styles[color];

  return (
    <div className={`rounded-xl border p-5 ${s.bg} ${s.border}`}>
      <h3 className={`text-xs font-semibold uppercase tracking-widest mb-3 ${s.heading}`}>
        {title}
      </h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-800 flex items-start gap-2">
            <span className={`mt-0.5 shrink-0 ${s.dot}`}>&#x2022;</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ComparisonView({ data }: { data: ComparisonResponse }) {
  return (
    <div className="space-y-5">
      {/* Snapshot cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        <SnapshotCard snapshot={data.target} isTarget />
        {data.competitors.map((c) => (
          <SnapshotCard key={c.business_id} snapshot={c} isTarget={false} />
        ))}
      </div>

      {/* AI comparison summary */}
      {data.comparison_summary && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            Comparison Summary
          </h3>
          <p className="text-gray-800 leading-relaxed text-[15px]">
            {data.comparison_summary}
          </p>
        </div>
      )}

      {/* Strengths / Weaknesses / Opportunities */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <InsightColumn title="Strengths" items={data.strengths} color="green" />
        <InsightColumn title="Weaknesses" items={data.weaknesses} color="red" />
        <InsightColumn title="Opportunities" items={data.opportunities} color="blue" />
      </div>
    </div>
  );
}
