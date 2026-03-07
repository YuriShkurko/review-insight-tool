import type { InsightItem } from "@/lib/types";

interface InsightListProps {
  title: string;
  items: InsightItem[];
  emptyText?: string;
}

export default function InsightList({
  title,
  items,
  emptyText = "No data yet",
}: InsightListProps) {
  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">
        {title}
      </h3>
      {items.length === 0 ? (
        <p className="text-gray-400 text-sm">{emptyText}</p>
      ) : (
        <ul className="space-y-2">
          {items.map((item, i) => (
            <li key={i} className="flex items-center justify-between text-sm">
              <span>{item.label}</span>
              <span className="bg-gray-100 text-gray-600 px-2 py-0.5 rounded text-xs font-medium">
                {item.count}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
