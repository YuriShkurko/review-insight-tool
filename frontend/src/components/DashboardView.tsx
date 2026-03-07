import type { Dashboard } from "@/lib/types";
import InsightList from "./InsightList";

function StatCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5 text-center">
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-sm text-gray-500 mt-1">{label}</p>
    </div>
  );
}

export default function DashboardView({ data }: { data: Dashboard }) {
  const hasInsights =
    data.top_complaints.length > 0 || data.top_praise.length > 0;

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <StatCard
          value={data.avg_rating !== null ? data.avg_rating.toFixed(1) : "—"}
          label="Average Rating"
        />
        <StatCard
          value={String(data.total_reviews)}
          label="Total Reviews"
        />
        <StatCard
          value={
            hasInsights
              ? String(data.top_complaints.length + data.top_praise.length)
              : "—"
          }
          label="Insights Found"
        />
      </div>

      {data.ai_summary && (
        <div className="bg-white border border-gray-200 rounded-lg p-5">
          <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-2">
            AI Summary
          </h3>
          <p className="text-gray-800 leading-relaxed">{data.ai_summary}</p>
        </div>
      )}

      {hasInsights && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <InsightList
            title="Top Complaints"
            items={data.top_complaints}
            emptyText="No complaints found"
          />
          <InsightList
            title="Top Praise"
            items={data.top_praise}
            emptyText="No praise found"
          />
        </div>
      )}
    </div>
  );
}
