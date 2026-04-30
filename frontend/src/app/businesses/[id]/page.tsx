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
import { ResizablePanel } from "@/components/ui/ResizablePanel";
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
      <div className="flex justify-center items-center h-[calc(100dvh-3rem)] bg-surface">
        <span className="inline-block h-5 w-5 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="max-w-4xl mx-auto py-8 px-4">
        <Link
          href="/businesses"
          className="text-sm text-text-muted hover:text-text-secondary mb-4 inline-flex items-center gap-1 transition-colors"
        >
          <span aria-hidden>&larr;</span> Back to businesses
        </Link>
        <div className="text-center py-16 bg-surface-card border border-border rounded-xl px-4">
          <p className="text-text-secondary mb-6 max-w-md mx-auto leading-relaxed">{loadError}</p>
          <Link
            href="/businesses"
            className="inline-flex items-center justify-center bg-brand text-white px-5 py-2.5 rounded-lg text-sm font-medium hover:bg-brand-hover transition-colors"
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
  activeTab: "workspace" | "chat";
  setActiveTab: (tab: "workspace" | "chat") => void;
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
    <div className="h-[calc(100dvh-3rem)] flex flex-col overflow-hidden bg-surface">
      {toast && <Toast message={toast.message} type={toast.type} onDone={() => setToast(null)} />}

      {/* Header */}
      <header className="shrink-0 bg-surface-card border-b border-border px-4 py-2.5">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <Link
              href="/businesses"
              className="shrink-0 text-sm text-text-muted hover:text-text-secondary transition-colors"
            >
              &larr; Back
            </Link>
            <span className="text-border shrink-0" aria-hidden>
              |
            </span>
            <h1 className="font-semibold text-text-primary truncate">{dashboard.business_name}</h1>
            {dashboard.business_type && dashboard.business_type !== "other" && (
              <span className="shrink-0 hidden sm:inline-block text-xs bg-surface-elevated text-text-muted px-2 py-0.5 rounded-full capitalize border border-border-subtle">
                {dashboard.business_type}
              </span>
            )}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              onClick={onFetchReviews}
              disabled={busy}
              className="border border-border bg-surface-card text-text-secondary px-3 py-1.5 rounded-lg text-sm hover:bg-surface-elevated disabled:opacity-50 transition-colors"
            >
              {fetchingReviews ? "Fetching…" : hasReviews ? "Refresh" : "Fetch Reviews"}
            </button>
            <button
              type="button"
              onClick={onAnalyze}
              disabled={busy || !hasReviews}
              title={!hasReviews ? "Fetch reviews first" : undefined}
              className="bg-brand text-white px-3 py-1.5 rounded-lg text-sm hover:bg-brand-hover disabled:opacity-50 transition-colors"
            >
              {analyzing ? "Analyzing…" : hasAnalysis ? "Re-analyze" : "Analyze"}
            </button>
          </div>
        </div>

        {actionError && <p className="mt-1.5 text-xs text-red-500">{actionError}</p>}
      </header>

      {/* Mobile tab bar */}
      <div className="lg:hidden shrink-0 bg-surface-card border-b border-border flex">
        <button
          type="button"
          onClick={() => setActiveTab("workspace")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "workspace" ? "text-brand border-b-2 border-brand" : "text-text-muted"
          }`}
        >
          Dashboard{state.widgets.length > 0 ? ` (${state.widgets.length})` : ""}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("chat")}
          className={`flex-1 py-2.5 text-sm font-medium transition-colors ${
            activeTab === "chat" ? "text-brand border-b-2 border-brand" : "text-text-muted"
          }`}
        >
          Chat
        </button>
      </div>

      {/* Desktop: resizable panel. Mobile: tab-based */}
      <div className="flex-1 overflow-hidden hidden lg:flex">
        <ResizablePanel
          left={
            <Workspace
              widgets={state.widgets}
              onDelete={handleDeleteWidget}
              onReorder={handleReorder}
              isLoading={state.isLoading}
              error={state.error}
              onRetry={reload}
              onDismissError={dismissError}
            />
          }
          right={<ChatPanel key={id} businessId={id} onCollapse={onCollapseChat} />}
          defaultRatio={0.65}
          rightCollapsed={chatCollapsed}
          onRightCollapsedChange={onExpandChat}
        />
      </div>

      {/* Mobile panels */}
      <div className="flex-1 overflow-hidden flex flex-col lg:hidden">
        <div
          className={`${activeTab === "workspace" ? "flex" : "hidden"} flex-col flex-1 overflow-hidden`}
        >
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
          className={`${activeTab === "chat" ? "flex" : "hidden"} flex-col flex-1 overflow-hidden`}
        >
          <ChatPanel key={id} businessId={id} />
        </div>
      </div>
    </div>
  );
}
