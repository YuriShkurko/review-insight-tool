"use client";

import type {
  ComparisonResponse,
  BusinessSnapshot,
} from "@/lib/types";

function SnapshotCard({
  snapshot,
  isTarget,
}: {
  snapshot: BusinessSnapshot;
  isTarget: boolean;
}) {
  return (
    <div
      className={`rounded-lg p-4 border ${
        isTarget
          ? "border-blue-300 bg-blue-50/50"
          : "border-gray-200 bg-white"
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <h4 className="font-semibold">{snapshot.name}</h4>
        {isTarget && (
          <span className="text-xs bg-blue-200 text-blue-800 px-2 py-0.5 rounded-full">
            Your business
          </span>
        )}
        {snapshot.business_type && snapshot.business_type !== "other" && (
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
            {snapshot.business_type}
          </span>
        )}
      </div>
      <div className="flex gap-4 text-sm text-gray-600 mb-2">
        <span>
          {snapshot.avg_rating != null
            ? `★ ${snapshot.avg_rating.toFixed(1)}`
            : "—"}
        </span>
        <span>{snapshot.total_reviews} reviews</span>
      </div>
      <p className="text-sm text-gray-700 line-clamp-3">{snapshot.summary}</p>
      {(snapshot.top_complaints.length > 0 || snapshot.top_praise.length > 0) && (
        <div className="mt-3 pt-3 border-t border-gray-200 grid grid-cols-2 gap-2 text-xs">
          {snapshot.top_complaints.length > 0 && (
            <div>
              <span className="text-gray-500 font-medium">Complaints: </span>
              {snapshot.top_complaints.slice(0, 2).map((c) => c.label).join(", ")}
            </div>
          )}
          {snapshot.top_praise.length > 0 && (
            <div>
              <span className="text-gray-500 font-medium">Praise: </span>
              {snapshot.top_praise.slice(0, 2).map((p) => p.label).join(", ")}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function StringList({
  title,
  items,
  icon,
}: {
  title: string;
  items: string[];
  icon: string;
}) {
  if (items.length === 0) return null;
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">
        {icon} {title}
      </h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-gray-800 text-sm flex items-start gap-2">
            <span className="text-gray-400 mt-0.5 shrink-0">•</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function ComparisonView({ data }: { data: ComparisonResponse }) {
  return (
    <div className="space-y-6">
      <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide">
        Comparison
      </h3>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <SnapshotCard snapshot={data.target} isTarget />
        {data.competitors.map((c) => (
          <SnapshotCard key={c.business_id} snapshot={c} isTarget={false} />
        ))}
      </div>

      {data.comparison_summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-2">
            Summary
          </h3>
          <p className="text-gray-800 leading-relaxed">
            {data.comparison_summary}
          </p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StringList
          title="Strengths vs competitors"
          items={data.strengths}
          icon="✓"
        />
        <StringList
          title="Weaknesses vs competitors"
          items={data.weaknesses}
          icon="!"
        />
        <StringList
          title="Opportunities"
          items={data.opportunities}
          icon="→"
        />
      </div>
    </div>
  );
}
