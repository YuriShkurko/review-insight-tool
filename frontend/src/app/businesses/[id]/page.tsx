"use client";

import { useEffect, useState, useCallback, useMemo, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import { trailEvent } from "@/lib/debugTrail";
import DashboardView from "@/components/DashboardView";
import ReviewList from "@/components/ReviewList";
import CompetitorSection from "@/components/CompetitorSection";
import ComparisonView from "@/components/ComparisonView";
import Toast from "@/components/Toast";
import type {
  CatalogBusiness,
  CatalogResponse,
  Dashboard,
  Review,
  ComparisonResponse,
  CompetitorRead,
} from "@/lib/types";

function CollapsibleSection({
  title,
  defaultOpen = true,
  children,
  id,
}: {
  title: string;
  defaultOpen?: boolean;
  children: React.ReactNode;
  id?: string;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <section id={id}>
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-2 mb-4 group w-full text-left"
      >
        <span
          className={`text-gray-300 text-xs transition-transform duration-200 ${open ? "rotate-90" : ""}`}
        >
          &#9654;
        </span>
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest group-hover:text-gray-600 transition-colors">
          {title}
        </h2>
      </button>
      <div
        className={`transition-all duration-200 overflow-hidden ${open ? "max-h-[5000px] opacity-100" : "max-h-0 opacity-0"}`}
      >
        {children}
      </div>
    </section>
  );
}

export default function BusinessDetailPage() {
  const { user, isLoading: authLoading } = useRequireAuth();
  const params = useParams();
  const id = params.id as string;

  const reviewsRef = useRef<HTMLDivElement>(null);
  /** Ignore late responses if the route `id` changed while a fetch was in flight. */
  const activeRouteIdRef = useRef(id);
  activeRouteIdRef.current = id;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [fetchingReviews, setFetchingReviews] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [actionError, setActionError] = useState("");
  const [competitors, setCompetitors] = useState<CompetitorRead[]>([]);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparisonError, setComparisonError] = useState("");
  const [sandboxCatalog, setSandboxCatalog] = useState<CatalogResponse | null>(null);
  const [analyzeAllBusy, setAnalyzeAllBusy] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);

  const catalogCompetitors = useMemo((): CatalogBusiness[] => {
    if (!sandboxCatalog || !dashboard?.place_id) return [];
    for (const s of sandboxCatalog.scenarios) {
      if (s.main.place_id === dashboard.place_id) {
        return s.competitors;
      }
    }
    return [];
  }, [sandboxCatalog, dashboard?.place_id]);

  const busy = fetchingReviews || analyzing || comparing || analyzeAllBusy;

  const competitorSectionRef = useRef<{ reload: () => Promise<void> }>(null);

  const handleCompetitorsChange = useCallback((comps: CompetitorRead[]) => {
    setCompetitors(comps);
    setComparison(null);
    setComparisonError("");
  }, []);

  const loadDashboard = useCallback(async () => {
    const routeId = id;
    const d = await apiFetch<Dashboard>(`/businesses/${routeId}/dashboard`);
    if (activeRouteIdRef.current !== routeId) return;
    setDashboard(d);
  }, [id]);

  const loadReviews = useCallback(async () => {
    const routeId = id;
    const r = await apiFetch<Review[]>(`/businesses/${routeId}/reviews`);
    if (activeRouteIdRef.current !== routeId) return;
    setReviews(r);
  }, [id]);

  const loadAll = useCallback(async () => {
    const routeId = id;
    trailEvent("biz:load-start", { businessId: routeId });
    setLoading(true);
    setLoadError("");
    try {
      await Promise.all([loadDashboard(), loadReviews()]);
      if (activeRouteIdRef.current !== routeId) return;
      trailEvent("biz:load-ok", { businessId: routeId });
    } catch (err) {
      if (activeRouteIdRef.current !== routeId) return;
      setDashboard(null);
      setReviews([]);
      setCompetitors([]);
      setComparison(null);
      if (err instanceof ApiError) {
        if (err.status === 404) {
          trailEvent("biz:load-fail", { businessId: routeId, status: 404, detail: err.detail });
          setLoadError(
            "This business is no longer available. It may have been deleted or the link is out of date.",
          );
        } else if (err.status === 422) {
          trailEvent("biz:load-fail", { businessId: routeId, status: 422, detail: err.detail });
          setLoadError("Invalid business link. Go back and open the business from your list.");
        } else {
          trailEvent("biz:load-fail", {
            businessId: routeId,
            status: err.status,
            detail: err.detail,
          });
          setLoadError(err.detail || "Failed to load business data.");
        }
      } else {
        trailEvent("biz:load-fail", { businessId: routeId, detail: "unknown error" });
        setLoadError("Failed to load business data.");
      }
    } finally {
      if (activeRouteIdRef.current === routeId) {
        setLoading(false);
      }
    }
  }, [loadDashboard, loadReviews, id]);

  useEffect(() => {
    if (!user) return;
    setDashboard(null);
    setReviews([]);
    setCompetitors([]);
    setComparison(null);
    setComparisonError("");
    setActionError("");
    setLoadError("");
    setLoading(true);
    loadAll();
  }, [user, id, loadAll]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    (async () => {
      try {
        const c = await apiFetch<CatalogResponse>("/sandbox/catalog");
        if (!cancelled) setSandboxCatalog(c);
      } catch {
        if (!cancelled) setSandboxCatalog(null);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user]);

  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
  }

  async function handleFetchReviews() {
    trailEvent("biz:fetch-reviews", { businessId: id });
    setFetchingReviews(true);
    setActionError("");
    try {
      const r = await apiFetch<Review[]>(`/businesses/${id}/fetch-reviews`, {
        method: "POST",
      });
      setReviews(r);
      await loadDashboard();
      showToast(`Fetched ${r.length} review${r.length !== 1 ? "s" : ""}.`);
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : "Failed to fetch reviews.");
    } finally {
      setFetchingReviews(false);
    }
  }

  async function handleAnalyze() {
    trailEvent("biz:analyze", { businessId: id });
    setAnalyzing(true);
    setActionError("");
    try {
      await apiFetch(`/businesses/${id}/analyze`, { method: "POST" });
      await loadDashboard();
      showToast("Analysis complete.");
    } catch (err) {
      setActionError(err instanceof ApiError ? err.detail : "Failed to run analysis.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleGenerateComparison() {
    trailEvent("biz:compare", { businessId: id, competitorCount: competitors.length });
    setComparing(true);
    setComparisonError("");
    setComparison(null);
    try {
      const data = await apiFetch<ComparisonResponse>(`/businesses/${id}/competitors/comparison`, {
        method: "POST",
      });
      setComparison(data);
      showToast("Comparison generated.");
    } catch (err) {
      setComparisonError(err instanceof ApiError ? err.detail : "Failed to generate comparison.");
    } finally {
      setComparing(false);
    }
  }

  async function handleAnalyzeAllAndCompare() {
    trailEvent("biz:analyze-all-compare", { businessId: id, competitorCount: competitors.length });
    setAnalyzeAllBusy(true);
    setActionError("");
    setComparisonError("");
    setComparison(null);
    try {
      const hasMainAnalysis = !!dashboard?.ai_summary;
      if (!hasMainAnalysis) {
        await apiFetch(`/businesses/${id}/analyze`, { method: "POST" });
        await loadDashboard();
      }

      for (const comp of competitors) {
        if (!comp.has_reviews) {
          await apiFetch(`/businesses/${comp.business.id}/fetch-reviews`, { method: "POST" });
        }
        if (!comp.has_analysis || !comp.has_reviews) {
          await apiFetch(`/businesses/${comp.business.id}/analyze`, { method: "POST" });
        }
      }

      await competitorSectionRef.current?.reload();

      const data = await apiFetch<ComparisonResponse>(`/businesses/${id}/competitors/comparison`, {
        method: "POST",
      });
      setComparison(data);
      showToast("All competitors analyzed & comparison generated.");
    } catch (err) {
      const msg = err instanceof ApiError ? err.detail : "Failed to analyze & compare.";
      setComparisonError(msg);
      showToast(msg, "error");
    } finally {
      setAnalyzeAllBusy(false);
    }
  }

  function scrollToReviews() {
    reviewsRef.current?.scrollIntoView({ behavior: "smooth" });
  }

  if (authLoading || loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="inline-block h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Link
          href="/businesses"
          className="text-sm text-gray-500 hover:text-gray-700 mb-4 inline-flex items-center gap-1"
        >
          <span aria-hidden>&larr;</span> Back to businesses
        </Link>
        <div className="text-center py-16 bg-white border border-gray-200 rounded-xl px-4">
          <p className="text-gray-700 mb-6 max-w-md mx-auto leading-relaxed">{loadError}</p>
          <div className="flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/businesses"
              className="inline-flex items-center justify-center bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
            >
              Back to your businesses
            </Link>
            <button
              type="button"
              onClick={() => {
                trailEvent("biz:retry", { businessId: id });
                loadAll();
              }}
              className="inline-flex items-center justify-center border border-gray-300 bg-white text-gray-800 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 transition-colors"
            >
              Retry loading
            </button>
          </div>
        </div>
      </div>
    );
  }

  const hasReviews = reviews.length > 0;
  const hasAnalysis = !!dashboard?.ai_summary;

  const mainReady = hasAnalysis;
  const anyCompReady = competitors.some((c) => c.has_analysis);
  const allCompReady = competitors.length > 0 && competitors.every((c) => c.has_analysis);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-8">
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Navigation */}
      <Link
        href="/businesses"
        className="text-sm text-gray-500 hover:text-gray-700 inline-flex items-center gap-1"
      >
        <span aria-hidden>&larr;</span> Back to businesses
      </Link>

      {dashboard && (
        <>
          {/* ── Header ── */}
          <header className="bg-white border border-gray-200 rounded-xl p-6">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="min-w-0">
                <div className="flex items-center gap-2.5 mb-1">
                  <h1 className="text-2xl font-bold tracking-tight truncate">
                    {dashboard.business_name}
                  </h1>
                  {dashboard.business_type && dashboard.business_type !== "other" && (
                    <span className="text-xs bg-gray-100 text-gray-600 px-2.5 py-0.5 rounded-full capitalize shrink-0">
                      {dashboard.business_type}
                    </span>
                  )}
                </div>
                {dashboard.address && <p className="text-gray-500 text-sm">{dashboard.address}</p>}
              </div>

              {/* Actions (Fitts's Law: prominent size for primary actions) */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={handleFetchReviews}
                  disabled={busy}
                  className={`border border-gray-300 bg-white text-gray-700 px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors ${fetchingReviews ? "animate-pulse-slow" : ""}`}
                >
                  {fetchingReviews ? "Fetching…" : hasReviews ? "Refresh Reviews" : "Fetch Reviews"}
                </button>
                <button
                  onClick={handleAnalyze}
                  disabled={busy || !hasReviews}
                  title={!hasReviews ? "Fetch reviews first" : undefined}
                  className={`bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors ${analyzing ? "animate-pulse-slow" : ""}`}
                >
                  {analyzing ? "Analyzing…" : hasAnalysis ? "Re-run Analysis" : "Run Analysis"}
                </button>
              </div>
            </div>

            {/* Feedback messages */}
            {actionError && (
              <p className="mt-4 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {actionError}
              </p>
            )}

            {/* Metadata strip */}
            {(hasReviews || hasAnalysis) && (
              <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-400">
                {dashboard.total_reviews > 0 && (
                  <button
                    type="button"
                    onClick={scrollToReviews}
                    className="hover:text-blue-600 transition-colors cursor-pointer"
                  >
                    {dashboard.total_reviews} reviews stored ↓
                  </button>
                )}
                {hasAnalysis && dashboard.analysis_created_at && (
                  <span>
                    Analysis:{" "}
                    {new Date(dashboard.analysis_created_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                )}
                {dashboard.last_updated_at && (
                  <span>
                    Updated:{" "}
                    {new Date(dashboard.last_updated_at).toLocaleDateString(undefined, {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </span>
                )}
              </div>
            )}
          </header>

          {/* ── Guidance ── */}
          {!hasReviews && !hasAnalysis && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 text-sm text-blue-800 space-y-1">
              <p>
                <strong>Step 1:</strong> Click <strong>Fetch Reviews</strong> to pull reviews for
                this business.
              </p>
              <p>
                <strong>Step 2:</strong> Click <strong>Run Analysis</strong> to generate AI-powered
                insights.
              </p>
            </div>
          )}
          {hasReviews && !hasAnalysis && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-sm text-amber-800">
              Reviews loaded. Click <strong>Run Analysis</strong> to generate AI-powered insights.
            </div>
          )}

          {/* ── Dashboard Insights ── */}
          {(hasReviews || hasAnalysis) && (
            <CollapsibleSection title="Insights">
              <DashboardView data={dashboard} onReviewsClick={scrollToReviews} />
            </CollapsibleSection>
          )}

          {/* ── Competitors ── */}
          <CollapsibleSection title="Competitors">
            <CompetitorSection
              ref={competitorSectionRef}
              businessId={id}
              onCompetitorsChange={handleCompetitorsChange}
              onCompetitorAnalyzed={handleGenerateComparison}
              catalogCompetitors={catalogCompetitors.length > 0 ? catalogCompetitors : undefined}
            />
          </CollapsibleSection>

          {/* ── Comparison ── */}
          {competitors.length > 0 && (
            <CollapsibleSection title="Comparison" id="comparison-section">
              <div className="space-y-4">
                {/* Prerequisites checklist */}
                <div className="bg-gray-50 border border-gray-200 rounded-xl p-4 space-y-2">
                  <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                    Comparison prerequisites
                  </p>
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
                    <span className={mainReady ? "text-green-700" : "text-gray-400"}>
                      {mainReady ? "✓" : "○"} Your business analyzed
                    </span>
                    <span className={allCompReady ? "text-green-700" : anyCompReady ? "text-amber-600" : "text-gray-400"}>
                      {allCompReady ? "✓" : anyCompReady ? "◐" : "→"}{" "}
                      {allCompReady
                        ? "All competitors analyzed"
                        : anyCompReady
                          ? "Some competitors analyzed — rest will auto-analyze"
                          : "Competitors will be auto-analyzed"}
                    </span>
                  </div>
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    type="button"
                    onClick={handleAnalyzeAllAndCompare}
                    disabled={busy || competitors.length === 0}
                    className={`bg-indigo-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors ${analyzeAllBusy ? "animate-pulse-slow" : ""}`}
                  >
                    {analyzeAllBusy
                      ? "Analyzing & Comparing…"
                      : allCompReady && mainReady
                        ? "Re-run Comparison"
                        : "Analyze All & Compare"}
                  </button>
                  {!analyzeAllBusy && !comparison && mainReady && anyCompReady && (
                    <button
                      type="button"
                      onClick={handleGenerateComparison}
                      disabled={busy}
                      className={`border border-indigo-300 text-indigo-700 px-4 py-2.5 rounded-lg text-sm font-medium hover:bg-indigo-50 disabled:opacity-50 transition-colors ${comparing ? "animate-pulse-slow" : ""}`}
                    >
                      {comparing ? "Generating…" : "Compare Ready Only"}
                    </button>
                  )}
                </div>
                {comparisonError && (
                  <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                    {comparisonError}
                  </p>
                )}
                {comparison && <ComparisonView data={comparison} />}
              </div>
            </CollapsibleSection>
          )}

          {/* Competitor hint when analysis done but no competitors */}
          {hasAnalysis && competitors.length === 0 && (
            <p className="text-xs text-gray-400 text-center">
              Want to see how you compare? Add competitors above and generate a comparison.
            </p>
          )}

          {/* ── Reviews ── */}
          {hasReviews && (
            <CollapsibleSection title="Reviews">
              <div ref={reviewsRef}>
                <ReviewList reviews={reviews} />
              </div>
            </CollapsibleSection>
          )}
        </>
      )}
    </div>
  );
}
