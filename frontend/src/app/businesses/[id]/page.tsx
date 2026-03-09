"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import DashboardView from "@/components/DashboardView";
import ReviewList from "@/components/ReviewList";
import type { Dashboard, Review } from "@/lib/types";

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

  const busy = fetchingReviews || analyzing;

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

  if (authLoading || loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="inline-block h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="max-w-3xl mx-auto py-8 px-4">
        <Link
          href="/businesses"
          className="text-sm text-blue-600 hover:underline mb-4 inline-block"
        >
          &larr; Back to businesses
        </Link>
        <div className="text-center py-16 bg-white border border-gray-200 rounded-lg">
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
    <div className="max-w-3xl mx-auto py-8 px-4">
      <Link
        href="/businesses"
        className="text-sm text-blue-600 hover:underline mb-4 inline-block"
      >
        &larr; Back to businesses
      </Link>

      {dashboard && (
        <>
          <div className="mb-6">
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-semibold">
                {dashboard.business_name}
              </h1>
              {dashboard.business_type && dashboard.business_type !== "other" && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full capitalize">
                  {dashboard.business_type}
                </span>
              )}
            </div>
            {dashboard.address && (
              <p className="text-gray-500 text-sm mt-1">
                {dashboard.address}
              </p>
            )}
          </div>

          {/* Actions */}
          <div className="flex flex-wrap items-center gap-3 mb-2">
            <button
              onClick={handleFetchReviews}
              disabled={busy}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
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
              className="bg-green-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-green-700 disabled:opacity-50 transition-colors"
            >
              {analyzing
                ? "Analyzing..."
                : hasAnalysis
                  ? "Re-run Analysis"
                  : "Run Analysis"}
            </button>
          </div>

          {/* Feedback messages */}
          {actionError && (
            <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-3 py-2 mb-4">
              {actionError}
            </p>
          )}
          {actionSuccess && !actionError && (
            <p className="text-green-700 text-sm bg-green-50 border border-green-200 rounded px-3 py-2 mb-4">
              {actionSuccess}
            </p>
          )}
          {!actionError && !actionSuccess && <div className="mb-4" />}

          {/* Workflow guidance when data is missing */}
          {!hasReviews && !hasAnalysis && (
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6 text-sm text-blue-800">
              Click <strong>Fetch Reviews</strong> to pull reviews for this
              business, then <strong>Run Analysis</strong> to generate AI
              insights.
            </div>
          )}
          {hasReviews && !hasAnalysis && (
            <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 text-sm text-amber-800">
              Reviews loaded. Click <strong>Run Analysis</strong> to generate
              AI-powered insights.
            </div>
          )}

          <DashboardView data={dashboard} />
        </>
      )}

      <div className="mt-6">
        <ReviewList reviews={reviews} />
      </div>
    </div>
  );
}
