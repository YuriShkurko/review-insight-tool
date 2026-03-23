"use client";

import {
  useEffect,
  useState,
  useCallback,
  useImperativeHandle,
  forwardRef,
  type FormEvent,
} from "react";
import { apiFetch, ApiError } from "@/lib/api";
import {
  BUSINESS_TYPES,
  type CatalogBusiness,
  type CompetitorRead,
  type BusinessType,
  type Review,
} from "@/lib/types";

const MAX_COMPETITORS = 3;

function StatusBadge({
  hasReviews,
  hasAnalysis,
  analysisAt,
}: {
  hasReviews: boolean;
  hasAnalysis: boolean;
  analysisAt?: string | null;
}) {
  if (hasAnalysis) {
    const dateStr = analysisAt
      ? new Date(analysisAt).toLocaleDateString(undefined, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })
      : null;
    return (
      <span
        className="inline-flex items-center gap-1 text-xs font-medium bg-green-50 text-green-700 border border-green-200 px-2.5 py-0.5 rounded-full"
        title={dateStr ? `Analyzed ${dateStr}` : undefined}
      >
        <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
        Ready{dateStr ? ` · ${dateStr}` : ""}
      </span>
    );
  }
  if (hasReviews) {
    return (
      <span className="inline-flex items-center gap-1 text-xs font-medium bg-amber-50 text-amber-700 border border-amber-200 px-2.5 py-0.5 rounded-full">
        <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
        Needs analysis
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium bg-gray-50 text-gray-500 border border-gray-200 px-2.5 py-0.5 rounded-full">
      <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
      No reviews
    </span>
  );
}

export interface CompetitorSectionHandle {
  reload: () => Promise<void>;
}

const CompetitorSection = forwardRef<
  CompetitorSectionHandle,
  {
    businessId: string;
    onCompetitorsChange?: (competitors: CompetitorRead[]) => void;
    onCompetitorAnalyzed?: () => void;
    catalogCompetitors?: CatalogBusiness[];
  }
>(function CompetitorSection(
  { businessId, onCompetitorsChange, onCompetitorAnalyzed, catalogCompetitors },
  ref,
) {
  const [competitors, setCompetitors] = useState<CompetitorRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [preparing, setPreparing] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [successMsg, setSuccessMsg] = useState("");
  const [input, setInput] = useState("");
  const [businessType, setBusinessType] = useState<BusinessType>("other");
  const [quickAddBusy, setQuickAddBusy] = useState<string | null>(null);

  const loadCompetitors = useCallback(async () => {
    try {
      const data = await apiFetch<CompetitorRead[]>(`/businesses/${businessId}/competitors`);
      setCompetitors(data);
      onCompetitorsChange?.(data);
    } catch {
      setCompetitors([]);
      onCompetitorsChange?.([]);
    } finally {
      setLoading(false);
    }
  }, [businessId, onCompetitorsChange]);

  useImperativeHandle(ref, () => ({ reload: loadCompetitors }), [loadCompetitors]);

  useEffect(() => {
    loadCompetitors();
  }, [loadCompetitors]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSuccessMsg("");
    setAdding(true);
    const trimmed = input.trim();
    const isUrl = trimmed.startsWith("http");
    const body = isUrl
      ? { google_maps_url: trimmed, place_id: null, business_type: businessType }
      : { place_id: trimmed, google_maps_url: null, business_type: businessType };
    try {
      await apiFetch<CompetitorRead>(`/businesses/${businessId}/competitors`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      await loadCompetitors();
      setInput("");
      setBusinessType("other");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to add competitor.");
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(competitorBusinessId: string) {
    setError("");
    setSuccessMsg("");
    setRemoving(competitorBusinessId);
    try {
      await apiFetch(`/businesses/${businessId}/competitors/${competitorBusinessId}`, {
        method: "DELETE",
      });
      await loadCompetitors();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to remove competitor.");
    } finally {
      setRemoving(null);
    }
  }

  function isLinkedPlace(placeId: string): boolean {
    return competitors.some((c) => c.business.place_id === placeId);
  }

  async function handleQuickAddSample(placeId: string) {
    setError("");
    setSuccessMsg("");
    setQuickAddBusy(placeId);
    try {
      await apiFetch(`/sandbox/import`, {
        method: "POST",
        body: JSON.stringify({
          place_id: placeId,
          as_competitor_for: businessId,
        }),
      });
      await loadCompetitors();
      setSuccessMsg("Sample competitor added. Fetch reviews & analyze when ready.");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to add sample competitor.");
    } finally {
      setQuickAddBusy(null);
    }
  }

  async function handlePrepare(competitorBusinessId: string, name: string) {
    setError("");
    setSuccessMsg("");
    setPreparing(competitorBusinessId);
    try {
      const reviews = await apiFetch<Review[]>(
        `/businesses/${competitorBusinessId}/fetch-reviews`,
        { method: "POST" },
      );
      await apiFetch(`/businesses/${competitorBusinessId}/analyze`, {
        method: "POST",
      });
      await loadCompetitors();
      setSuccessMsg(`${name}: ${reviews.length} reviews fetched & analyzed.`);
      onCompetitorAnalyzed?.();
    } catch (err) {
      setError(err instanceof ApiError ? `${name}: ${err.detail}` : `Failed to prepare ${name}.`);
    } finally {
      setPreparing(null);
    }
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-xl p-6">
        <div className="flex items-center gap-2 text-sm text-gray-400">
          <div className="h-4 w-4 border-2 border-gray-300 border-t-transparent rounded-full animate-spin" />
          Loading…
        </div>
      </div>
    );
  }

  const atLimit = competitors.length >= MAX_COMPETITORS;
  const anyBusy = !!removing || !!preparing || !!quickAddBusy;
  const samples = catalogCompetitors ?? [];

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-6 space-y-4">
      {samples.length > 0 && !atLimit && (
        <div className="rounded-lg border border-blue-100 bg-blue-50/40 p-4 space-y-2">
          <p className="text-xs font-semibold text-blue-900 uppercase tracking-wide">
            Quick add from samples
          </p>
          <p className="text-xs text-blue-800/80">
            Add curated offline competitors for this scenario. You still run Fetch &amp; Analyze
            yourself.
          </p>
          <div className="flex flex-wrap gap-2">
            {samples.map((row) => {
              const linked = isLinkedPlace(row.place_id);
              const busy = quickAddBusy === row.place_id;
              return (
                <button
                  key={row.place_id}
                  type="button"
                  disabled={linked || busy || anyBusy || adding}
                  onClick={() => handleQuickAddSample(row.place_id)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-blue-200 bg-white text-blue-800 hover:bg-blue-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {busy ? "Adding…" : linked ? `${row.name} (added)` : row.name}
                </button>
              );
            })}
          </div>
        </div>
      )}

      {/* Add form */}
      {!atLimit && (
        <form onSubmit={handleAdd} className="space-y-2">
          <div className="flex flex-wrap gap-2 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs text-gray-500 mb-1">
                Google Maps URL, shortened link, or place ID
              </label>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="https://maps.app.goo.gl/... or full Maps URL"
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div className="w-28">
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value as BusinessType)}
                className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm capitalize focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                {BUSINESS_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={adding || !input.trim()}
              className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors whitespace-nowrap"
            >
              {adding ? "Adding…" : "Add Competitor"}
            </button>
          </div>
          <p className="text-xs text-gray-400">Add up to {MAX_COMPETITORS} competitors.</p>
        </form>
      )}
      {atLimit && (
        <p className="text-xs text-gray-400">
          Maximum of {MAX_COMPETITORS} competitors reached. Remove one to add another.
        </p>
      )}

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      {successMsg && !error && (
        <p className="text-green-700 text-sm bg-green-50 border border-green-200 rounded-lg px-3 py-2">
          {successMsg}
        </p>
      )}

      {/* Competitor list */}
      {competitors.length === 0 ? (
        <div className="text-center py-6 border border-dashed border-gray-200 rounded-xl">
          <p className="text-sm text-gray-400">No competitors linked yet</p>
          <p className="text-xs text-gray-400 mt-1">Add a competitor above to start comparing</p>
        </div>
      ) : (
        <div className="space-y-2">
          {competitors.map(
            ({ link_id, business, has_reviews, has_analysis, analysis_created_at }) => (
              <div
                key={link_id}
                className="flex items-center gap-3 p-3 rounded-lg border border-gray-100 bg-gray-50/50 hover:bg-gray-50 transition-colors"
              >
                <div className="flex-1 min-w-0">
                  <span className="font-medium text-sm text-gray-900 truncate block">
                    {business.name}
                  </span>
                  {business.address && (
                    <span className="text-xs text-gray-400 truncate block">{business.address}</span>
                  )}
                  <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-400">
                    <span>
                      {business.avg_rating != null
                        ? `★ ${business.avg_rating.toFixed(1)}`
                        : "No rating"}
                    </span>
                    <span>
                      {business.total_reviews} review{business.total_reviews !== 1 ? "s" : ""}
                    </span>
                  </div>
                </div>
                <StatusBadge
                  hasReviews={has_reviews}
                  hasAnalysis={has_analysis}
                  analysisAt={analysis_created_at}
                />
                <button
                  type="button"
                  onClick={() => handlePrepare(business.id, business.name)}
                  disabled={anyBusy || adding}
                  className={`text-xs font-medium text-blue-600 hover:text-blue-700 disabled:opacity-50 transition-colors shrink-0 ${preparing === business.id ? "animate-pulse-slow" : ""}`}
                >
                  {preparing === business.id
                    ? "Preparing…"
                    : has_analysis
                      ? "Refresh"
                      : has_reviews
                        ? "Analyze"
                        : "Fetch & Analyze"}
                </button>
                <button
                  type="button"
                  onClick={() => handleRemove(business.id)}
                  disabled={anyBusy || adding}
                  className="text-xs text-gray-400 hover:text-red-600 disabled:opacity-50 transition-colors shrink-0"
                >
                  {removing === business.id ? "Removing…" : "Remove"}
                </button>
              </div>
            ),
          )}
        </div>
      )}
    </div>
  );
});

export default CompetitorSection;
