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

function StringList({ title, items, icon }: { title: string; items: string[]; icon: string }) {
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

export default function DashboardView({ data }: { data: Dashboard }) {
  const hasInsights =
    data.top_complaints.length > 0 || data.top_praise.length > 0;
  const hasAnalysis = !!(data.ai_summary);

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

      {data.recommended_focus && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h3 className="font-semibold text-sm text-blue-700 uppercase tracking-wide mb-1">
            Recommended Focus
          </h3>
          <p className="text-blue-900 text-sm">{data.recommended_focus}</p>
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

      {hasAnalysis && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <StringList
            title="Action Items"
            items={data.action_items}
            icon="💡"
          />
          <StringList
            title="Risk Areas"
            items={data.risk_areas}
            icon="⚠️"
          />
        </div>
      )}
    </div>
  );
}
