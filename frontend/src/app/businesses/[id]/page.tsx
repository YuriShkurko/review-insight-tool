"use client";

import { useEffect, useState, useCallback, useRef } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import { trailEvent } from "@/lib/debugTrail";
import Toast from "@/components/Toast";
import { ChatPanel } from "@/components/agent/ChatPanel";
import { Workspace } from "@/components/agent/Workspace";
import type { Dashboard, Review } from "@/lib/types";
import type { WorkspaceWidget } from "@/lib/agentTypes";

type ActiveTab = "workspace" | "chat";

export default function BusinessDetailPage() {
  const { user, isLoading: authLoading } = useRequireAuth();
  const params = useParams();
  const id = params.id as string;

  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [fetchingReviews, setFetchingReviews] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [actionError, setActionError] = useState("");
  const [toast, setToast] = useState<{ message: string; type: "success" | "error" } | null>(null);
  const [workspace, setWorkspace] = useState<WorkspaceWidget[]>([]);
  const [workspaceLoading, setWorkspaceLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<ActiveTab>("chat");

  const activeRouteIdRef = useRef(id);
  activeRouteIdRef.current = id;

  const busy = fetchingReviews || analyzing;

  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
  }

  const loadDashboard = useCallback(async () => {
    const routeId = id;
    const d = await apiFetch<Dashboard>(`/businesses/${routeId}/dashboard`);
    if (activeRouteIdRef.current !== routeId) return;
    setDashboard(d);
  }, [id]);

  const loadWorkspace = useCallback(async () => {
    const routeId = id;
    try {
      const w = await apiFetch<WorkspaceWidget[]>(`/businesses/${routeId}/agent/workspace`);
      if (activeRouteIdRef.current !== routeId) return;
      setWorkspace(w);
    } catch {
      // non-critical
    } finally {
      if (activeRouteIdRef.current === routeId) setWorkspaceLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!user) return;
    setDashboard(null);
    setLoadError("");
    setLoading(true);
    setWorkspaceLoading(true);
    setWorkspace([]);

    const routeId = id;
    trailEvent("biz:load-start", { businessId: routeId });

    (async () => {
      try {
        await loadDashboard();
        if (activeRouteIdRef.current !== routeId) return;
        trailEvent("biz:load-ok", { businessId: routeId });
      } catch (err) {
        if (activeRouteIdRef.current !== routeId) return;
        setDashboard(null);
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setLoadError(
              "This business is no longer available. It may have been deleted or the link is out of date.",
            );
          } else if (err.status === 422) {
            setLoadError("Invalid business link. Go back and open the business from your list.");
          } else {
            setLoadError(err.detail || "Failed to load business data.");
          }
        } else {
          setLoadError("Failed to load business data.");
        }
      } finally {
        if (activeRouteIdRef.current === routeId) setLoading(false);
      }
    })();

    loadWorkspace();
  }, [user, id, loadDashboard, loadWorkspace]);

  async function handleFetchReviews() {
    trailEvent("biz:fetch-reviews", { businessId: id });
    setFetchingReviews(true);
    setActionError("");
    try {
      const r = await apiFetch<Review[]>(`/businesses/${id}/fetch-reviews`, { method: "POST" });
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

  async function handleDeleteWidget(widgetId: string) {
    try {
      await apiFetch(`/businesses/${id}/agent/workspace/${widgetId}`, { method: "DELETE" });
      setWorkspace((ws) => ws.filter((w) => w.id !== widgetId));
    } catch {
      showToast("Failed to remove widget.", "error");
    }
  }

  const handleWidgetPinned = useCallback(async () => {
    await loadWorkspace();
    setActiveTab("workspace");
  }, [loadWorkspace]);

  if (authLoading || loading) {
    return (
      <div className="flex justify-center items-center h-screen">
        <span className="inline-block h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
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
          <Link
            href="/businesses"
            className="inline-flex items-center justify-center bg-blue-600 text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors"
          >
            Back to your businesses
          </Link>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  const hasReviews = dashboard.total_reviews > 0;
  const hasAnalysis = !!dashboard.ai_summary;

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-gray-50">
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Header */}
      <header className="shrink-0 bg-white border-b border-gray-200 px-4 py-3">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <Link
              href="/businesses"
              className="shrink-0 text-sm text-gray-400 hover:text-gray-600 transition-colors"
            >
              &larr; Back
            </Link>
            <span className="text-gray-200 shrink-0" aria-hidden>
              |
            </span>
            <h1 className="font-semibold text-gray-900 truncate">{dashboard.business_name}</h1>
            {dashboard.business_type && dashboard.business_type !== "other" && (
              <span className="shrink-0 hidden sm:inline-block text-xs bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full capitalize">
                {dashboard.business_type}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={handleFetchReviews}
              disabled={busy}
              className="border border-gray-200 bg-white text-gray-700 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50 transition-colors"
            >
              {fetchingReviews ? "Fetching…" : hasReviews ? "Refresh" : "Fetch Reviews"}
            </button>
            <button
              type="button"
              onClick={handleAnalyze}
              disabled={busy || !hasReviews}
              title={!hasReviews ? "Fetch reviews first" : undefined}
              className="bg-blue-600 text-white px-3 py-1.5 rounded-lg text-sm hover:bg-blue-700 disabled:opacity-50 transition-colors"
            >
              {analyzing ? "Analyzing…" : hasAnalysis ? "Re-analyze" : "Analyze"}
            </button>
          </div>
        </div>

        {actionError && <p className="mt-2 text-xs text-red-600">{actionError}</p>}
      </header>

      {/* Mobile tab bar */}
      <div className="md:hidden shrink-0 bg-white border-b border-gray-200 flex">
        <button
          type="button"
          onClick={() => setActiveTab("workspace")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "workspace" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500"
          }`}
        >
          Workspace{workspace.length > 0 ? ` (${workspace.length})` : ""}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("chat")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "chat" ? "text-blue-600 border-b-2 border-blue-600" : "text-gray-500"
          }`}
        >
          Chat
        </button>
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden flex">
        {/* Workspace panel */}
        <div
          className={`${
            activeTab === "workspace" ? "flex" : "hidden"
          } md:flex flex-col w-full md:w-[42%] lg:w-[38%] border-r border-gray-200 bg-gray-50 overflow-hidden`}
        >
          <Workspace
            widgets={workspace}
            onDelete={handleDeleteWidget}
            isLoading={workspaceLoading}
          />
        </div>

        {/* Chat panel */}
        <div
          className={`${
            activeTab === "chat" ? "flex" : "hidden"
          } md:flex flex-col flex-1 bg-white overflow-hidden`}
        >
          <ChatPanel key={id} businessId={id} onWidgetPinned={handleWidgetPinned} />
        </div>
      </div>
    </div>
  );
}
