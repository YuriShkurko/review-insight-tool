"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { ChatPanel } from "@/components/agent/ChatPanel";
import { CommandBar } from "@/components/agent/CommandBar";
import { ExecutiveSummary } from "@/components/agent/ExecutiveSummary";
import { Workspace } from "@/components/agent/Workspace";
import Toast from "@/components/Toast";
import { apiFetch, ApiError } from "@/lib/api";
import { useRequireAuth } from "@/lib/auth";
import { flattenForReorder, groupBySection } from "@/lib/dashboardSections";
import { displayBusinessName } from "@/lib/displayName";
import { trailEvent } from "@/lib/debugTrail";
import { useAgentChat } from "@/lib/useAgentChat";
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
  const [presentationMode, setPresentationMode] = useState(false);
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

  function handleTogglePresentationMode() {
    setPresentationMode((current) => {
      const next = !current;
      if (next) setActiveTab("workspace");
      return next;
    });
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
        key={id}
        id={id}
        dashboard={dashboard}
        toast={toast}
        setToast={setToast}
        actionError={actionError}
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        presentationMode={presentationMode}
        onTogglePresentationMode={handleTogglePresentationMode}
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
  presentationMode,
  onTogglePresentationMode,
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
  presentationMode: boolean;
  onTogglePresentationMode: () => void;
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
  const onAgentStreamDone = useCallback(async () => {
    await reload();
  }, [reload]);
  const chat = useAgentChat(id, undefined, onAgentStreamDone, dispatch);

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

  const handleCleanLayoutCommand = useCallback(() => {
    const ordered = [...state.widgets].sort((a, b) => a.position - b.position);
    if (ordered.length < 2) return;
    const cleanIds = flattenForReorder(groupBySection(ordered));
    void handleReorder(cleanIds);
  }, [handleReorder, state.widgets]);

  const hasReviews = dashboard.total_reviews > 0;
  const hasAnalysis = !!dashboard.ai_summary;

  return (
    <div
      data-presentation-mode={presentationMode ? "true" : "false"}
      className="flex h-[calc(100dvh-3rem)] flex-col overflow-hidden bg-[#0f172a]"
    >
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
              <h1 className="truncate font-semibold text-white">
                {displayBusinessName({
                  place_id: dashboard.place_id,
                  name: dashboard.business_name,
                })}
              </h1>
              <p className="hidden text-xs text-white/45 sm:block">
                AI-assisted business insight workspace
              </p>
            </div>
            {dashboard.business_type && dashboard.business_type !== "other" && (
              <span className="hidden shrink-0 rounded-full border border-white/10 bg-white/[0.06] px-2 py-0.5 text-xs capitalize text-white/60 sm:inline-block">
                {dashboard.business_type}
              </span>
            )}
          </div>

          <div className="flex shrink-0 items-center gap-2">
            {!presentationMode && (
              <>
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
              </>
            )}
            <button
              type="button"
              data-testid="presentation-mode-toggle"
              onClick={onTogglePresentationMode}
              className={`rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                presentationMode
                  ? "border border-amber-300/40 bg-amber-300 text-[#111827] hover:bg-amber-200"
                  : "border border-white/15 bg-white/[0.06] text-white/80 hover:bg-white/[0.1]"
              }`}
            >
              {presentationMode ? "Exit presentation" : "Present"}
            </button>
          </div>
        </div>

        {actionError && !presentationMode && (
          <p className="mt-1.5 text-xs text-red-300">{actionError}</p>
        )}
      </header>

      {!presentationMode && (
        <CommandBar
          isStreaming={chat.isStreaming}
          canCleanLayout={state.widgets.length >= 2}
          onSendPrompt={(prompt) => void chat.sendMessage(prompt)}
          onCleanLayout={handleCleanLayoutCommand}
          onTogglePresentationMode={onTogglePresentationMode}
        />
      )}

      <div
        className={`shrink-0 border-b border-white/10 bg-[#111827] p-1 lg:hidden ${
          presentationMode ? "hidden" : "flex"
        }`}
      >
        <button
          type="button"
          onClick={() => setActiveTab("workspace")}
          className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition-colors ${
            activeTab === "workspace" ? "bg-surface-card text-text-primary" : "text-white/55"
          }`}
        >
          Dashboard{state.widgets.length > 0 ? ` (${state.widgets.length})` : ""}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("chat")}
          className={`flex-1 rounded-lg py-2.5 text-sm font-medium transition-colors ${
            activeTab === "chat" ? "bg-surface-card text-text-primary" : "text-white/55"
          }`}
        >
          Assistant
        </button>
      </div>

      <div
        data-testid="dashboard-desktop"
        className="relative hidden flex-1 overflow-hidden bg-surface lg:flex lg:flex-col"
      >
        {/* Keep workspace chrome clear of the fixed assistant panel (same width as aside: right-5 + w). */}
        <div
          className={`flex min-h-0 flex-1 flex-col overflow-hidden ${
            !presentationMode && !chatCollapsed ? "pr-[calc(1.25rem+min(430px,34vw))]" : ""
          }`}
        >
          <Workspace
            widgets={state.widgets}
            onDelete={handleDeleteWidget}
            onReorder={handleReorder}
            isLoading={state.isLoading}
            error={state.error}
            onRetry={reload}
            onDismissError={dismissError}
            presentationMode={presentationMode}
            scrollHeader={<ExecutiveSummary dashboard={dashboard} />}
          />
        </div>
        {!presentationMode && !chatCollapsed ? (
          <aside
            data-testid="assistant-drawer"
            className="animate-panel-in absolute bottom-5 right-5 top-5 z-20 w-[min(430px,34vw)] overflow-hidden rounded-lg border border-white/15 bg-surface-card shadow-2xl"
          >
            <ChatPanel businessId={id} chat={chat} onCollapse={onCollapseChat} />
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
          className={`${activeTab === "workspace" || presentationMode ? "flex" : "hidden"} flex-1 flex-col overflow-hidden`}
        >
          <Workspace
            widgets={state.widgets}
            onDelete={handleDeleteWidget}
            onReorder={handleReorder}
            isLoading={state.isLoading}
            error={state.error}
            onRetry={reload}
            onDismissError={dismissError}
            presentationMode={presentationMode}
            scrollHeader={<ExecutiveSummary dashboard={dashboard} />}
          />
        </div>
        <div
          className={`${activeTab === "chat" && !presentationMode ? "flex" : "hidden"} flex-1 flex-col overflow-hidden bg-surface-card`}
        >
          <ChatPanel businessId={id} chat={chat} />
        </div>
      </div>
    </div>
  );
}
