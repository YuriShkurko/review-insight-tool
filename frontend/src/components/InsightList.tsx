import type { InsightItem } from "@/lib/types";

interface InsightListProps {
  title: string;
  items: InsightItem[];
  emptyText?: string;
  color?: "red" | "green" | "gray";
}

const COLORS = {
  red: {
    badge: "bg-red-100 text-red-700",
    bar: "bg-red-400",
  },
  green: {
    badge: "bg-green-100 text-green-700",
    bar: "bg-green-400",
  },
  gray: {
    badge: "bg-gray-100 text-gray-600",
    bar: "bg-gray-400",
  },
};

export default function InsightList({
  title,
  items,
  emptyText = "No data yet",
  color = "gray",
}: InsightListProps) {
  const palette = COLORS[color];
  const maxCount = items.reduce((max, it) => Math.max(max, it.count), 1);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-3">
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="text-gray-400 text-sm">{emptyText}</p>
      ) : (
        <ul className="space-y-2.5">
          {items.map((item, i) => (
            <li key={i} className="space-y-1">
              <div className="flex items-center justify-between text-sm">
                <span className="text-gray-800">{item.label}</span>
                <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${palette.badge}`}>
                  {item.count}
                </span>
              </div>
              <div className="h-1 rounded-full bg-gray-100 overflow-hidden">
                <div
                  className={`h-full rounded-full ${palette.bar}`}
                  style={{ width: `${(item.count / maxCount) * 100}%` }}
                />
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
