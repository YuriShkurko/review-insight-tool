import Link from "next/link";
import type { Business } from "@/lib/types";

export default function BusinessCard({ business }: { business: Business }) {
  return (
    <Link
      href={`/businesses/${business.id}`}
      className="block bg-white border border-gray-200 rounded-xl p-5 hover:shadow-md hover:border-gray-300 transition-all"
    >
      <div className="flex items-center gap-2 mb-1">
        <h3 className="font-semibold text-base text-gray-900 truncate">
          {business.name}
        </h3>
        {business.business_type && business.business_type !== "other" && (
          <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full capitalize shrink-0">
            {business.business_type}
          </span>
        )}
      </div>
      {business.address && (
        <p className="text-gray-400 text-sm truncate">{business.address}</p>
      )}
      <div className="flex items-center gap-4 mt-2.5 text-sm">
        <span className="font-semibold text-gray-800">
          {business.avg_rating !== null
            ? `★ ${business.avg_rating.toFixed(1)}`
            : "No rating"}
        </span>
        <span className="text-gray-400 text-xs">
          {business.total_reviews} review{business.total_reviews !== 1 && "s"}
        </span>
      </div>
    </Link>
  );
}
