import type { Dashboard } from "@/lib/types";
import InsightList from "./InsightList";

function StatCard({
  value,
  label,
  accent,
}: {
  value: string;
  label: string;
  accent?: "blue" | "default";
}) {
  const ring = accent === "blue" ? "border-blue-200 bg-blue-50/40" : "border-gray-200 bg-white";
  return (
    <div className={`rounded-xl border p-5 text-center ${ring}`}>
      <p className="text-3xl font-bold tracking-tight">{value}</p>
      <p className="text-xs text-gray-500 mt-1 uppercase tracking-wide">{label}</p>
    </div>
  );
}

function BulletList({
  title,
  items,
  color,
}: {
  title: string;
  items: string[];
  color: "blue" | "amber" | "gray";
}) {
  if (items.length === 0) return null;
  const colors = {
    blue: "border-blue-200 bg-blue-50/30",
    amber: "border-amber-200 bg-amber-50/30",
    gray: "border-gray-200 bg-white",
  };
  const dots = {
    blue: "text-blue-400",
    amber: "text-amber-400",
    gray: "text-gray-400",
  };
  return (
    <div className={`rounded-xl border p-5 ${colors[color]}`}>
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
        {title}
      </h3>
      <ul className="space-y-2">
        {items.map((item, i) => (
          <li key={i} className="text-sm text-gray-800 flex items-start gap-2">
            <span className={`mt-0.5 shrink-0 ${dots[color]}`}>&#x2022;</span>
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default function DashboardView({ data }: { data: Dashboard }) {
  const hasInsights = data.top_complaints.length > 0 || data.top_praise.length > 0;
  const hasAnalysis = !!data.ai_summary;

  return (
    <div className="space-y-5">
      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        <StatCard
          value={data.avg_rating !== null ? data.avg_rating.toFixed(1) : "—"}
          label="Avg Rating"
          accent="blue"
        />
        <StatCard value={String(data.total_reviews)} label="Reviews" />
        <StatCard
          value={hasInsights ? String(data.top_complaints.length + data.top_praise.length) : "—"}
          label="Insights"
        />
      </div>

      {/* AI Summary */}
      {data.ai_summary && (
        <div className="bg-white border border-gray-200 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-2">
            AI Summary
          </h3>
          <p className="text-gray-800 leading-relaxed text-[15px]">{data.ai_summary}</p>
        </div>
      )}

      {/* Recommended Focus */}
      {data.recommended_focus && (
        <div className="bg-blue-50 border border-blue-200 rounded-xl p-5">
          <h3 className="text-xs font-semibold text-blue-600 uppercase tracking-widest mb-1">
            Recommended Focus
          </h3>
          <p className="text-blue-900 text-sm font-medium">{data.recommended_focus}</p>
        </div>
      )}

      {/* Complaints & Praise */}
      {hasInsights && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <InsightList
            title="Top Complaints"
            items={data.top_complaints}
            emptyText="No complaints found"
            color="red"
          />
          <InsightList
            title="Top Praise"
            items={data.top_praise}
            emptyText="No praise found"
            color="green"
          />
        </div>
      )}

      {/* Action Items & Risk Areas */}
      {hasAnalysis && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <BulletList title="Action Items" items={data.action_items} color="blue" />
          <BulletList title="Risk Areas" items={data.risk_areas} color="amber" />
        </div>
      )}
    </div>
  );
}
