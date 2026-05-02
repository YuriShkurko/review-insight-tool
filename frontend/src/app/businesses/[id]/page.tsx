"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChatPanel } from "@/components/agent/ChatPanel";
import { ExecutiveSummary } from "@/components/agent/ExecutiveSummary";
import { Workspace } from "@/components/agent/Workspace";
import Toast from "@/components/Toast";
import { apiFetch, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { trailEvent } from "@/lib/debugTrail";
import { WorkspaceBlackboardProvider, useWorkspace } from "@/lib/workspaceBlackboard";
import type { Dashboard, Review } from "@/lib/types";

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
  const [activeTab, setActiveTab] = useState<ActiveTab>("workspace");
  const [chatCollapsed, setChatCollapsed] = useState(() => {
    try {
      return localStorage.getItem("chat-collapsed") === "true";
    } catch {
      return false;
    }
  });

  const activeRouteIdRef = useRef(id);
  activeRouteIdRef.current = id;

  const busy = fetchingReviews || analyzing;

  function showToast(message: string, type: "success" | "error" = "success") {
    setToast({ message, type });
  }

  function handleCollapseChat() {
    setChatCollapsed(true);
    try {
      localStorage.setItem("chat-collapsed", "true");
    } catch {}
  }

  function handleExpandChat() {
    setChatCollapsed(false);
    try {
      localStorage.setItem("chat-collapsed", "false");
    } catch {}
  }

  const loadDashboard = useCallback(async () => {
    const routeId = id;
    const d = await apiFetch<Dashboard>(`/businesses/${routeId}/dashboard`);
    if (activeRouteIdRef.current !== routeId) return;
    setDashboard(d);
  }, [id]);

  useEffect(() => {
    if (!user) return;
    setDashboard(null);
    setLoadError("");
    setLoading(true);

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
  }, [user, id, loadDashboard]);

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

  if (authLoading || loading) {
    return (
      <div className="flex h-[calc(100dvh-3rem)] items-center justify-center bg-[#0f172a]">
        <span className="inline-block h-5 w-5 animate-spin rounded-full border-2 border-brand border-t-transparent" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <Link
          href="/businesses"
          className="mb-4 inline-flex items-center gap-1 text-sm text-text-muted transition-colors hover:text-text-secondary"
        >
          Back to businesses
        </Link>
        <div className="rounded-lg border border-border bg-surface-card px-4 py-16 text-center">
          <p className="mx-auto mb-6 max-w-md leading-relaxed text-text-secondary">{loadError}</p>
          <Link
            href="/businesses"
            className="inline-flex items-center justify-center rounded-lg bg-brand px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-brand-hover"
          >
            Back to your businesses
          </Link>
        </div>
      </div>
    );
  }

  if (!dashboard) return null;

  return (
    <WorkspaceBlackboardProvider businessId={id}>
      <BusinessDetailContent
        id={id}
        dashboard={dashboard}
        toast={toast}
        setToast={setToast}
        actionError={actionError}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        chatCollapsed={chatCollapsed}
        onCollapseChat={handleCollapseChat}
        onExpandChat={handleExpandChat}
        fetchingReviews={fetchingReviews}
        analyzing={analyzing}
        busy={busy}
        onFetchReviews={handleFetchReviews}
        onAnalyze={handleAnalyze}
      />
    </WorkspaceBlackboardProvider>
  );
}

function BusinessDetailContent({
  id,
  dashboard,
  toast,
  setToast,
  actionError,
  activeTab,
  setActiveTab,
  chatCollapsed,
  onCollapseChat,
  onExpandChat,
  fetchingReviews,
  analyzing,
  busy,
  onFetchReviews,
  onAnalyze,
}: {
  id: string;
  dashboard: Dashboard;
  toast: { message: string; type: "success" | "error" } | null;
  setToast: (t: { message: string; type: "success" | "error" } | null) => void;
  actionError: string;
  activeTab: ActiveTab;
  setActiveTab: (tab: ActiveTab) => void;
  chatCollapsed: boolean;
  onCollapseChat: () => void;
  onExpandChat: () => void;
  fetchingReviews: boolean;
  analyzing: boolean;
  busy: boolean;
  onFetchReviews: () => void;
  onAnalyze: () => void;
}) {
  const { state, dispatch, reload } = useWorkspace();
  const dismissError = useCallback(() => dispatch({ type: "CLEAR_ERROR" }), [dispatch]);

  const handleDeleteWidget = useCallback(
    async (widgetId: string) => {
      dispatch({ type: "WIDGET_REMOVED", widgetId });
      try {
        await apiFetch(`/businesses/${id}/agent/workspace/${widgetId}`, { method: "DELETE" });
      } catch {
        setToast({ message: "Failed to remove widget.", type: "error" });
        await reload();
      }
    },
    [id, dispatch, reload, setToast],
  );

  const handleReorder = useCallback(
    async (widgetIds: string[]) => {
      dispatch({ type: "WIDGET_REORDERED", widgetIds });
      try {
        await apiFetch(`/businesses/${id}/agent/workspace/reorder`, {
          method: "PATCH",
          body: JSON.stringify({ widget_ids: widgetIds }),
        });
      } catch {
        await reload();
      }
    },
    [id, dispatch, reload],
  );

  const hasReviews = dashboard.total_reviews > 0;
  const hasAnalysis = !!dashboard.ai_summary;

  return (
    <div className="flex h-[calc(100dvh-3rem)] flex-col overflow-hidden bg-[#0f172a]">
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      <header className="shrink-0 border-b border-white/10 bg-[#0f172a] px-4 py-3 text-white">
        <div className="flex items-center justify-between gap-4">
          <div className="flex min-w-0 items-center gap-3">
            <Link
              href="/businesses"
              className="shrink-0 text-sm text-white/55 transition-colors hover:text-white"
            >
              Back
            </Link>
            <span className="shrink-0 text-white/20" aria-hidden>
              |
            </span>
            <div className="min-w-0">
              <h1 className="truncate font-semibold text-white">{dashboard.business_name}</h1>
              <p className="hidden text-xs text-white/45 sm:block">
                AI-assisted customer voice workspace
              </p>
            </div>
            {dashboard.business_type && dashboard.business_type !== "other" && (
              <span className="hidden shrink-0 rounded-full border border-white/10 bg-white/[0.06] px-2 py-0.5 text-xs capitalize text-white/60 sm:inline-block">
                {dashboard.business_type}
              </span>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={onFetchReviews}
              disabled={busy}
              className="rounded-lg border border-white/15 bg-white/[0.06] px-3 py-1.5 text-sm text-white/80 transition-colors hover:bg-white/[0.1] disabled:opacity-50"
            >
              {fetchingReviews ? "Fetching..." : hasReviews ? "Refresh" : "Fetch Reviews"}
            </button>
            <button
              type="button"
              onClick={onAnalyze}
              disabled={busy || !hasReviews}
              title={!hasReviews ? "Fetch reviews first" : undefined}
              className="rounded-lg bg-brand px-3 py-1.5 text-sm text-white transition-colors hover:bg-brand-hover disabled:opacity-50"
            >
              {analyzing ? "Analyzing..." : hasAnalysis ? "Re-analyze" : "Analyze"}
            </button>
          </div>
        </div>

        {actionError && <p className="mt-1.5 text-xs text-red-300">{actionError}</p>}
      </header>

      <div className="flex shrink-0 border-b border-white/10 bg-[#111827] p-1 lg:hidden">
        <button
          type="button"
          onClick={() => setActiveTab("workspace")}
          className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition-colors ${
            activeTab === "workspace" ? "bg-white text-[#111827]" : "text-white/55"
          }`}
        >
          Dashboard{state.widgets.length > 0 ? ` (${state.widgets.length})` : ""}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("chat")}
          className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition-colors ${
            activeTab === "chat" ? "bg-white text-[#111827]" : "text-white/55"
          }`}
        >
          Assistant
        </button>
      </div>

      <div
        data-testid="dashboard-desktop"
        className="relative hidden flex-1 overflow-hidden bg-[#f6f7fb] lg:flex lg:flex-col"
      >
        <ExecutiveSummary dashboard={dashboard} />
        <Workspace
          widgets={state.widgets}
          onDelete={handleDeleteWidget}
          onReorder={handleReorder}
          isLoading={state.isLoading}
          error={state.error}
          onRetry={reload}
          onDismissError={dismissError}
        />
        {!chatCollapsed ? (
          <aside
            data-testid="assistant-drawer"
            className="animate-panel-in absolute bottom-5 right-5 top-5 z-20 w-[min(430px,34vw)] overflow-hidden rounded-lg border border-white/15 bg-white shadow-2xl"
          >
            <ChatPanel key={id} businessId={id} onCollapse={onCollapseChat} />
          </aside>
        ) : (
          <button
            type="button"
            onClick={onExpandChat}
            className="absolute bottom-6 right-6 z-20 flex items-center gap-2 rounded-full bg-[#111827] px-4 py-2 text-sm font-medium text-white shadow-xl transition-all hover:-translate-y-0.5 hover:bg-brand"
          >
            Open Assistant
          </button>
        )}
      </div>

      <div
        data-testid="dashboard-mobile"
        className="flex flex-1 flex-col overflow-hidden lg:hidden"
      >
        <div
          className={`${activeTab === "workspace" ? "flex" : "hidden"} flex-1 flex-col overflow-hidden`}
        >
          <ExecutiveSummary dashboard={dashboard} />
          <Workspace
            widgets={state.widgets}
            onDelete={handleDeleteWidget}
            onReorder={handleReorder}
            isLoading={state.isLoading}
            error={state.error}
            onRetry={reload}
            onDismissError={dismissError}
          />
        </div>
        <div
          className={`${activeTab === "chat" ? "flex" : "hidden"} flex-1 flex-col overflow-hidden bg-white`}
        >
          <ChatPanel key={id} businessId={id} />
        </div>
      </div>
    </div>
  );
}
