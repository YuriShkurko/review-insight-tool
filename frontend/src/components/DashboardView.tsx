import type { Dashboard } from "@/lib/types";
import InsightList from "./InsightList";

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

function ratingColor(rating: number | null): string {
  if (rating === null) return "text-gray-400";
  if (rating >= 4.0) return "text-green-600";
  if (rating >= 3.0) return "text-amber-500";
  return "text-red-500";
}

export default function DashboardView({
  data,
  onReviewsClick,
}: {
  data: Dashboard;
  onReviewsClick?: () => void;
}) {
  const hasInsights = data.top_complaints.length > 0 || data.top_praise.length > 0;
  const hasAnalysis = !!data.ai_summary;

  return (
    <div className="space-y-5">
      {/* Hero metrics row — rating is the star (Von Restorff + Fitts's Law) */}
      <div className="grid grid-cols-1 sm:grid-cols-[1fr_auto_1fr] gap-3 items-stretch">
        {/* Rating — hero card, largest number (Serial Position + Visual Hierarchy) */}
        <div className="rounded-xl border border-blue-200 bg-gradient-to-b from-blue-50/60 to-white p-6 text-center flex flex-col justify-center">
          <p className={`text-5xl font-extrabold tracking-tight ${ratingColor(data.avg_rating)}`}>
            {data.avg_rating !== null ? data.avg_rating.toFixed(1) : "—"}
          </p>
          <p className="text-xs text-gray-500 mt-1.5 uppercase tracking-wide font-medium">
            Avg Rating
          </p>
        </div>

        {/* Secondary stats (Chunking — group related smaller numbers) */}
        <div className="flex sm:flex-col gap-3 min-w-[120px]">
          {/* Reviews — clickable (Goal-Gradient: jump to content) */}
          {onReviewsClick && data.total_reviews > 0 ? (
            <button
              type="button"
              onClick={onReviewsClick}
              className="flex-1 rounded-xl border border-gray-200 bg-white p-4 text-center hover:ring-2 hover:ring-blue-300 transition-all cursor-pointer"
            >
              <p className="text-2xl font-bold tracking-tight text-gray-900">
                {data.total_reviews}
              </p>
              <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-wide">Reviews ↓</p>
            </button>
          ) : (
            <div className="flex-1 rounded-xl border border-gray-200 bg-white p-4 text-center">
              <p className="text-2xl font-bold tracking-tight text-gray-900">
                {data.total_reviews}
              </p>
              <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-wide">Reviews</p>
            </div>
          )}

          <div className="flex-1 rounded-xl border border-gray-200 bg-white p-4 text-center">
            <p className="text-2xl font-bold tracking-tight text-gray-900">
              {hasInsights ? String(data.top_complaints.length + data.top_praise.length) : "—"}
            </p>
            <p className="text-[10px] text-gray-500 mt-1 uppercase tracking-wide">Insights</p>
          </div>
        </div>

        {/* Recommended Focus — standout card (Von Restorff) */}
        {data.recommended_focus ? (
          <div className="rounded-xl border-2 border-blue-300 bg-blue-50 p-5 flex flex-col justify-center">
            <h3 className="text-[10px] font-bold text-blue-600 uppercase tracking-widest mb-2">
              #1 Priority
            </h3>
            <p className="text-sm text-blue-900 font-medium leading-relaxed">
              {data.recommended_focus}
            </p>
          </div>
        ) : (
          <div className="rounded-xl border border-gray-200 bg-white p-5 flex items-center justify-center">
            <p className="text-sm text-gray-300">Run analysis to see your #1 priority</p>
          </div>
        )}
      </div>

      {/* AI Summary — prominent, full width (Cognitive Load: summary first) */}
      {data.ai_summary && (
        <div className="bg-white border border-gray-200 rounded-xl p-6">
          <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
            AI Summary
          </h3>
          <p className="text-gray-800 leading-relaxed text-base">{data.ai_summary}</p>
        </div>
      )}

      {/* Complaints & Praise (Chunking — paired side by side) */}
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

      {/* Action Items & Risk Areas (lower priority — bottom per Serial Position) */}
      {hasAnalysis && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <BulletList title="Action Items" items={data.action_items} color="blue" />
          <BulletList title="Risk Areas" items={data.risk_areas} color="amber" />
        </div>
      )}
    </div>
  );
}
