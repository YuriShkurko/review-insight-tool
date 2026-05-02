import Link from "next/link";
import type { Business } from "@/lib/types";
import { displayBusinessName } from "@/lib/displayName";
import { BusinessTypeIcon } from "@/components/icons/BusinessTypeIcon";

function formatRating(value: number | null): string {
  return value == null ? "No rating" : `${value.toFixed(1)} / 5`;
}

function formatUpdated(value: string): string {
  const diff = Date.now() - new Date(value).getTime();
  const hours = Math.max(0, Math.floor(diff / 3_600_000));
  if (hours < 1) return "Updated just now";
  if (hours < 24) return `Updated ${hours}h ago`;
  return `Updated ${Math.floor(hours / 24)}d ago`;
}

function getStatus(business: Business): { label: string; detail: string; tone: string } {
  if (business.total_reviews <= 0) {
    return {
      label: "Needs reviews",
      detail: "Fetch reviews before building an insight dashboard.",
      tone: "border-slate-200 bg-slate-50 text-slate-600",
    };
  }
  if (business.avg_rating != null) {
    return {
      label: "Demo ready",
      detail: "Reviews are loaded and ready for analysis.",
      tone: "border-emerald-200 bg-emerald-50 text-emerald-700",
    };
  }
  return {
    label: "Review data ready",
    detail: "Open the workspace to analyze customer voice.",
    tone: "border-brand/20 bg-brand-light text-brand",
  };
}

export default function BusinessCard({
  business,
  onDelete,
  deleting,
  featured = false,
}: {
  business: Business;
  onDelete?: (id: string) => void;
  deleting?: boolean;
  featured?: boolean;
}) {
  const status = getStatus(business);

  return (
    <article
      data-testid="business-tile"
      data-business-id={business.id}
      className={`group rounded-lg border bg-white p-5 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md ${
        featured ? "border-brand/30 ring-2 ring-brand/10" : "border-slate-200"
      }`}
    >
      <div className="flex h-full flex-col gap-5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              {featured && (
                <span className="rounded-full border border-brand/20 bg-brand-light px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-brand">
                  Recommended demo
                </span>
              )}
              {business.business_type && business.business_type !== "other" && (
                <span className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-slate-50 px-2 py-0.5 text-[10px] font-medium capitalize text-slate-500">
                  <BusinessTypeIcon
                    businessType={business.business_type}
                    className="h-3 w-3 text-slate-500"
                  />
                  {business.business_type}
                </span>
              )}
            </div>
            <h3 className="mt-2 flex items-center gap-2 truncate text-lg font-semibold text-text-primary">
              <BusinessTypeIcon
                businessType={business.business_type}
                className="h-5 w-5 shrink-0 text-text-muted"
                aria-hidden
              />
              <span className="truncate">{displayBusinessName(business)}</span>
            </h3>
            {business.address && (
              <p className="mt-1 line-clamp-2 text-sm leading-relaxed text-text-muted">
                {business.address}
              </p>
            )}
          </div>

          {onDelete && (
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                onDelete(business.id);
              }}
              disabled={deleting}
              className="shrink-0 rounded-md px-2 py-1 text-xs text-text-muted transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          )}
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
              Rating
            </p>
            <p className="mt-1 text-sm font-semibold text-text-primary">
              {formatRating(business.avg_rating)}
            </p>
          </div>
          <div className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
            <p className="text-[10px] font-medium uppercase tracking-wider text-text-muted">
              Reviews
            </p>
            <p className="mt-1 text-sm font-semibold text-text-primary">
              {business.total_reviews.toLocaleString()}
            </p>
          </div>
        </div>

        <div className={`rounded-lg border px-3 py-2 text-sm ${status.tone}`}>
          <p className="font-semibold">{status.label}</p>
          <p className="mt-0.5 text-xs opacity-80">{status.detail}</p>
        </div>

        <div className="mt-auto flex items-center justify-between gap-3 border-t border-slate-100 pt-4">
          <span className="text-xs text-text-muted">{formatUpdated(business.updated_at)}</span>
          <Link
            href={`/businesses/${business.id}`}
            data-testid="open-business-workspace"
            className="inline-flex items-center justify-center rounded-lg bg-[#111827] px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-brand"
          >
            Open workspace
          </Link>
        </div>
      </div>
    </article>
  );
}
