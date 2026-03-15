"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import DashboardView from "@/components/DashboardView";
import ReviewList from "@/components/ReviewList";
import CompetitorSection from "@/components/CompetitorSection";
import ComparisonView from "@/components/ComparisonView";
import type { Dashboard, Review, ComparisonResponse, CompetitorRead } from "@/lib/types";

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest mb-4">
      {children}
    </h2>
  );
}

export default function BusinessDetailPage() {
  const { user, isLoading: authLoading } = useRequireAuth();
  const params = useParams();
  const id = params.id as string;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [fetchingReviews, setFetchingReviews] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [actionError, setActionError] = useState("");
  const [actionSuccess, setActionSuccess] = useState("");
  const [competitors, setCompetitors] = useState<CompetitorRead[]>([]);
  const [comparison, setComparison] = useState<ComparisonResponse | null>(null);
  const [comparing, setComparing] = useState(false);
  const [comparisonError, setComparisonError] = useState("");

  const busy = fetchingReviews || analyzing || comparing;

  const handleCompetitorsChange = useCallback((comps: CompetitorRead[]) => {
    setCompetitors(comps);
    setComparison(null);
    setComparisonError("");
  }, []);

  const loadDashboard = useCallback(async () => {
    const d = await apiFetch<Dashboard>(`/businesses/${id}/dashboard`);
    setDashboard(d);
  }, [id]);

  const loadReviews = useCallback(async () => {
    try {
      const r = await apiFetch<Review[]>(`/businesses/${id}/reviews`);
      setReviews(r);
    } catch {
      /* reviews may not exist yet */
    }
  }, [id]);

  const loadAll = useCallback(async () => {
    setLoadError("");
    try {
      await Promise.all([loadDashboard(), loadReviews()]);
    } catch (err) {
      setLoadError(
        err instanceof ApiError && err.status === 404
          ? "Business not found."
          : "Failed to load business data."
      );
    } finally {
      setLoading(false);
    }
  }, [loadDashboard, loadReviews]);

  useEffect(() => {
    if (!user) return;
    loadAll();
  }, [user, loadAll]);

  function clearMessages() {
    setActionError("");
    setActionSuccess("");
  }

  async function handleFetchReviews() {
    setFetchingReviews(true);
    clearMessages();
    try {
      const r = await apiFetch<Review[]>(`/businesses/${id}/fetch-reviews`, {
        method: "POST",
      });
      setReviews(r);
      await loadDashboard();
      setActionSuccess(
        `Fetched ${r.length} review${r.length !== 1 ? "s" : ""}. Previous analysis was cleared — run analysis again for updated insights.`
      );
    } catch (err) {
      setActionError(
        err instanceof ApiError ? err.detail : "Failed to fetch reviews."
      );
    } finally {
      setFetchingReviews(false);
    }
  }

  async function handleAnalyze() {
    setAnalyzing(true);
    clearMessages();
    try {
      await apiFetch(`/businesses/${id}/analyze`, { method: "POST" });
      await loadDashboard();
      setActionSuccess("Analysis complete.");
    } catch (err) {
      setActionError(
        err instanceof ApiError
          ? err.detail
          : "Failed to run analysis."
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleGenerateComparison() {
    setComparing(true);
    setComparisonError("");
    setComparison(null);
    try {
      const data = await apiFetch<ComparisonResponse>(
        `/businesses/${id}/competitors/comparison`,
        { method: "POST" }
      );
      setComparison(data);
    } catch (err) {
      setComparisonError(
        err instanceof ApiError
          ? err.detail
          : "Failed to generate comparison."
      );
    } finally {
      setComparing(false);
    }
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
        <div className="text-center py-16 bg-white border border-gray-200 rounded-xl">
          <p className="text-gray-500 mb-3">{loadError}</p>
          <button
            onClick={loadAll}
            className="text-blue-600 hover:underline text-sm font-medium"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  const hasReviews = reviews.length > 0;
  const hasAnalysis = !!(dashboard?.ai_summary);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-8">
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
                {dashboard.address && (
                  <p className="text-gray-500 text-sm">{dashboard.address}</p>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={handleFetchReviews}
                  disabled={busy}
                  className="border border-gray-300 bg-white text-gray-700 px-4 py-2 rounded-lg text-sm font-medium hover:bg-gray-50 disabled:opacity-50 transition-colors"
                >
                  {fetchingReviews
                    ? "Fetching..."
                    : hasReviews
                      ? "Refresh Reviews"
                      : "Fetch Reviews"}
                </button>
                <button
                  onClick={handleAnalyze}
                  disabled={busy || !hasReviews}
                  title={!hasReviews ? "Fetch reviews first" : undefined}
                  className="bg-blue-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
                >
                  {analyzing
                    ? "Analyzing..."
                    : hasAnalysis
                      ? "Re-run Analysis"
                      : "Run Analysis"}
                </button>
              </div>
            </div>

            {/* Feedback messages */}
            {actionError && (
              <p className="mt-4 text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-3 py-2">
                {actionError}
              </p>
            )}
            {actionSuccess && !actionError && (
              <p className="mt-4 text-green-700 text-sm bg-green-50 border border-green-200 rounded-lg px-3 py-2">
                {actionSuccess}
              </p>
            )}

            {/* Metadata strip */}
            {(hasReviews || hasAnalysis) && (
              <div className="mt-4 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-400">
                {dashboard.total_reviews > 0 && (
                  <span>{dashboard.total_reviews} reviews stored</span>
                )}
                {hasAnalysis && dashboard.analysis_created_at && (
                  <span>
                    Analysis:{" "}
                    {new Date(dashboard.analysis_created_at).toLocaleDateString(
                      undefined,
                      { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" }
                    )}
                  </span>
                )}
                {dashboard.last_updated_at && (
                  <span>
                    Updated:{" "}
                    {new Date(dashboard.last_updated_at).toLocaleDateString(
                      undefined,
                      { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" }
                    )}
                  </span>
                )}
              </div>
            )}
          </header>

          {/* ── Guidance ── */}
          {!hasReviews && !hasAnalysis && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 text-sm text-blue-800 space-y-1">
              <p><strong>Step 1:</strong> Click <strong>Fetch Reviews</strong> to pull reviews for this business.</p>
              <p><strong>Step 2:</strong> Click <strong>Run Analysis</strong> to generate AI-powered insights.</p>
            </div>
          )}
          {hasReviews && !hasAnalysis && (
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-sm text-amber-800">
              Reviews loaded. Click <strong>Run Analysis</strong> to generate AI-powered insights.
            </div>
          )}

          {/* ── Dashboard Insights ── */}
          {(hasReviews || hasAnalysis) && (
            <section>
              <SectionHeading>Insights</SectionHeading>
              <DashboardView data={dashboard} />
            </section>
          )}

          {/* ── Competitors ── */}
          <section>
            <SectionHeading>Competitors</SectionHeading>
            <CompetitorSection
              businessId={id}
              onCompetitorsChange={handleCompetitorsChange}
            />
          </section>

          {/* ── Comparison ── */}
          {competitors.length > 0 && (
            <section>
              <SectionHeading>Comparison</SectionHeading>
              <div className="space-y-4">
                {!hasAnalysis && (
                  <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                    Run analysis on this business before generating a comparison.
                  </p>
                )}
                {hasAnalysis && !competitors.some((c) => c.has_analysis) && (
                  <p className="text-sm text-amber-700 bg-amber-50 border border-amber-200 rounded-lg px-4 py-3">
                    Fetch reviews and run analysis on at least one competitor before comparing.
                  </p>
                )}
                <div className="flex items-center gap-3">
                  <button
                    type="button"
                    onClick={handleGenerateComparison}
                    disabled={busy || !hasAnalysis || !competitors.some((c) => c.has_analysis)}
                    title={
                      !hasAnalysis
                        ? "Run analysis on this business first"
                        : !competitors.some((c) => c.has_analysis)
                          ? "At least one competitor needs analysis"
                          : undefined
                    }
                    className="bg-indigo-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                  >
                    {comparing ? "Generating…" : "Generate Comparison"}
                  </button>
                  {!comparing && !comparison && (
                    <span className="text-xs text-gray-400">
                      Compares with competitors that have analysis.
                    </span>
                  )}
                </div>
                {comparisonError && (
                  <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-lg px-4 py-3">
                    {comparisonError}
                  </p>
                )}
                {comparison && <ComparisonView data={comparison} />}
              </div>
            </section>
          )}

          {/* Competitor hint when analysis done but no competitors */}
          {hasAnalysis && competitors.length === 0 && (
            <p className="text-xs text-gray-400 text-center">
              Want to see how you compare? Add competitors above and generate a comparison.
            </p>
          )}

          {/* ── Reviews ── */}
          {hasReviews && (
            <section>
              <SectionHeading>Reviews</SectionHeading>
              <ReviewList reviews={reviews} />
            </section>
          )}
        </>
      )}
    </div>
  );
}
