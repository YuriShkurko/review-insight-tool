import Link from "next/link";
import type { Business } from "@/lib/types";

export default function BusinessCard({ business }: { business: Business }) {
  return (
    <Link
      href={`/businesses/${business.id}`}
      className="block bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-center gap-2">
        <h3 className="font-semibold text-lg">{business.name}</h3>
        {business.business_type && business.business_type !== "other" && (
          <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
            {business.business_type}
          </span>
        )}
      </div>
      {business.address && (
        <p className="text-gray-500 text-sm mt-1">{business.address}</p>
      )}
      <div className="flex gap-4 mt-3 text-sm">
        <span className="text-gray-700">
          {business.avg_rating !== null
            ? `★ ${business.avg_rating.toFixed(1)}`
            : "No rating"}
        </span>
        <span className="text-gray-500">
          {business.total_reviews} review{business.total_reviews !== 1 && "s"}
        </span>
      </div>
    </Link>
  );
}
