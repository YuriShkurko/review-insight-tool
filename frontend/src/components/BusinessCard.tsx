import Link from "next/link";
import type { Business } from "@/lib/types";

export default function BusinessCard({
  business,
  onDelete,
  deleting,
}: {
  business: Business;
  onDelete?: (id: string) => void;
  deleting?: boolean;
}) {
  return (
    <div className="bg-surface-card border border-border rounded-xl p-5 hover:shadow-md hover:border-border-subtle transition-all flex items-start gap-4">
      <Link href={`/businesses/${business.id}`} className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-1">
          <h3 className="font-semibold text-base text-text-primary truncate">{business.name}</h3>
          {business.business_type && business.business_type !== "other" && (
            <span className="text-[10px] bg-surface-elevated text-text-muted px-2 py-0.5 rounded-full capitalize shrink-0 border border-border-subtle">
              {business.business_type}
            </span>
          )}
        </div>
        {business.address && (
          <p className="text-text-muted text-sm truncate">{business.address}</p>
        )}
        <div className="flex items-center gap-4 mt-2.5 text-sm">
          <span className="font-semibold text-text-primary">
            {business.avg_rating !== null ? `★ ${business.avg_rating.toFixed(1)}` : "No rating"}
          </span>
          <span className="text-text-muted text-xs">
            {business.total_reviews} review{business.total_reviews !== 1 && "s"}
          </span>
        </div>
      </Link>
      {onDelete && (
        <button
          type="button"
          onClick={(e) => {
            e.preventDefault();
            onDelete(business.id);
          }}
          disabled={deleting}
          className="text-xs text-text-muted hover:text-red-500 disabled:opacity-50 transition-colors shrink-0 mt-1"
        >
          {deleting ? "Deleting…" : "Delete"}
        </button>
      )}
    </div>
  );
}
