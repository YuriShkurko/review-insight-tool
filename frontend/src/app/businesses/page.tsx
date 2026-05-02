"use client";

import { useEffect, useState, useCallback, type FormEvent } from "react";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import { trailEvent } from "@/lib/debugTrail";
import BusinessCard from "@/components/BusinessCard";
import SandboxCatalog from "@/components/SandboxCatalog";
import { displayBusinessName } from "@/lib/displayName";
import {
  BUSINESS_TYPES,
  type AppBootstrap,
  type Business,
  type BusinessType,
  type CatalogResponse,
} from "@/lib/types";

export default function BusinessesPage() {
  const { user, isLoading } = useRequireAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [businessType, setBusinessType] = useState<BusinessType>("other");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null);
  const [busyPlaceId, setBusyPlaceId] = useState<string | null>(null);
  const [resetBusy, setResetBusy] = useState(false);
  const [reviewProvider, setReviewProvider] = useState<string | null>(null);

  const isOfflineDemo = reviewProvider === "offline";
  const recommendedBusiness =
    businesses.find((b) => b.place_id === "sim_lager_ale_tlv") ??
    businesses.find((b) => b.place_id === "offline_lager_ale") ??
    [...businesses].sort((a, b) => b.total_reviews - a.total_reviews)[0] ??
    null;

  const sortedBusinesses = (() => {
    const others = businesses.filter((b) => b.id !== recommendedBusiness?.id);
    others.sort(
      (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
    return recommendedBusiness ? [recommendedBusiness, ...others] : others;
  })();

  const loadBusinesses = useCallback(async () => {
    try {
      setLoadError("");
      const data = await apiFetch<Business[]>("/businesses");
      setBusinesses(data);
    } catch {
      setLoadError("Could not load your businesses. Please try refreshing.");
    }
  }, []);

  const loadCatalog = useCallback(async () => {
    try {
      const data = await apiFetch<CatalogResponse>("/sandbox/catalog");
      setCatalog(data);
    } catch {
      setCatalog(null);
    }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadBusinesses(), loadCatalog()]);
  }, [loadBusinesses, loadCatalog]);

  useEffect(() => {
    if (!user) return;
    let cancelled = false;
    setLoading(true);
    (async () => {
      try {
        await refreshAll();
        try {
          const b = await apiFetch<AppBootstrap>("/bootstrap");
          if (!cancelled) setReviewProvider(b.review_provider);
        } catch {
          if (!cancelled) setReviewProvider("mock");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [user, refreshAll]);

  async function handleImportPlace(placeId: string) {
    trailEvent("sandbox:import", { placeId });
    setBusyPlaceId(placeId);
    setError("");
    try {
      await apiFetch<Business>("/sandbox/import", {
        method: "POST",
        body: JSON.stringify({ place_id: placeId }),
      });
      await refreshAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to add sample business.");
    } finally {
      setBusyPlaceId(null);
    }
  }

  async function handleResetSandbox() {
    if (
      !confirm(
        "Remove all offline sample businesses from your account? Reviews and analysis for those businesses will be deleted.",
      )
    )
      return;
    trailEvent("sandbox:reset");
    setResetBusy(true);
    setError("");
    try {
      await apiFetch("/sandbox/reset", { method: "POST" });
      await refreshAll();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Reset failed.");
    } finally {
      setResetBusy(false);
    }
  }

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError("");
    setAdding(true);

    const trimmed = input.trim();
    const isUrl = trimmed.startsWith("http");
    const body = isUrl
      ? { google_maps_url: trimmed, place_id: null, business_type: businessType }
      : { place_id: trimmed, google_maps_url: null, business_type: businessType };

    trailEvent("biz:add", { isUrl, businessType });
    try {
      const biz = await apiFetch<Business>("/businesses", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setBusinesses((prev) => [biz, ...prev]);
      setInput("");
      setBusinessType("other");
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to add business.");
    } finally {
      setAdding(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Delete this business and all its reviews, analysis, and competitor links?"))
      return;
    trailEvent("biz:delete", { businessId: id });
    setDeletingId(id);
    setError("");
    try {
      await apiFetch(`/businesses/${id}`, { method: "DELETE" });
      setBusinesses((prev) => prev.filter((b) => b.id !== id));
      await loadCatalog();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "Failed to delete business.");
    } finally {
      setDeletingId(null);
    }
  }

  if (isLoading || loading) {
    return (
      <div className="flex min-h-[50vh] items-center justify-center bg-[#f6f7fb]">
        <div className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-sm text-text-secondary shadow-sm">
          <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-brand border-t-transparent align-[-2px]" />
          Loading workspaces
        </div>
      </div>
    );
  }

  return (
    <div
      data-testid="business-launcher"
      className="min-h-[calc(100dvh-3rem)] bg-[#f6f7fb] px-4 py-6 sm:px-6 lg:px-8"
    >
      <div className="mx-auto max-w-7xl space-y-6">
        <section className="rounded-lg bg-[#111827] px-5 py-6 text-white shadow-sm sm:px-7">
          <div className="grid gap-6 lg:grid-cols-[1.35fr_1fr] lg:items-end">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-widest text-white/45">
                Review Insight
              </p>
              <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
                Your review intelligence workspaces
              </h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed text-white/65">
                Pick a business, open its AI dashboard, and turn customer voice into a demo-ready
                story.
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs text-white/65">
                <span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1">
                  {businesses.length} workspace{businesses.length !== 1 ? "s" : ""}
                </span>
                <span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1">
                  {isOfflineDemo ? "Offline demo mode" : "Live provider mode"}
                </span>
                {recommendedBusiness && (
                  <span className="rounded-full border border-white/10 bg-white/[0.06] px-3 py-1">
                    Recommended: {displayBusinessName(recommendedBusiness)}
                  </span>
                )}
              </div>
            </div>

            {isOfflineDemo ? (
              <div className="rounded-lg border border-white/10 bg-white/[0.06] p-4 text-sm text-white/70">
                <p className="font-semibold text-white">Offline demo mode</p>
                <p className="mt-1 leading-relaxed">
                  Add a curated sample from the catalog below. Google Maps links are disabled in
                  this mode so demos stay deterministic.
                </p>
              </div>
            ) : (
              <form onSubmit={handleAdd} className="rounded-lg border border-white/10 bg-white p-3">
                <div className="grid gap-2 sm:grid-cols-[1fr_auto]">
                  <input
                    type="text"
                    required
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Paste Google Maps URL or place ID"
                    disabled={adding}
                    className="min-w-0 rounded-lg border border-slate-200 px-3 py-2 text-sm text-text-primary focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={adding || !input.trim()}
                    className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-brand-hover disabled:opacity-50"
                  >
                    {adding ? "Adding..." : "Add workspace"}
                  </button>
                </div>
                <select
                  value={businessType}
                  onChange={(e) => setBusinessType(e.target.value as BusinessType)}
                  disabled={adding}
                  className="mt-2 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm capitalize text-text-secondary focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20 disabled:opacity-50"
                >
                  {BUSINESS_TYPES.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </form>
            )}
          </div>
        </section>

        {error && (
          <p className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
            {error}
          </p>
        )}

        {loadError ? (
          <div className="rounded-lg border border-slate-200 bg-white px-6 py-12 text-center">
            <p className="mb-3 text-text-secondary">{loadError}</p>
            <button
              onClick={() => refreshAll()}
              className="text-sm font-medium text-brand transition-colors hover:text-brand-hover"
            >
              Retry
            </button>
          </div>
        ) : businesses.length === 0 ? (
          <div className="space-y-6">
            {catalog ? (
              <SandboxCatalog
                catalog={catalog}
                onImportPlace={handleImportPlace}
                busyPlaceId={busyPlaceId}
                onResetSandbox={handleResetSandbox}
                resetBusy={resetBusy}
                variant="full"
              />
            ) : (
              <div className="bg-surface-card border border-border rounded-xl p-8">
                <h2 className="text-lg font-semibold text-text-primary mb-1">
                  Welcome to Review Insight
                </h2>
                <p className="text-text-secondary text-sm mb-5">
                  Understand what your customers are saying — in three simple steps.
                </p>
                <ol className="space-y-3 text-sm text-text-secondary">
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center h-6 w-6 rounded-full bg-brand-light text-brand text-xs font-bold shrink-0">
                      1
                    </span>
                    <span>
                      <strong className="text-text-primary">Add your business</strong> —{" "}
                      {isOfflineDemo ? (
                        <>
                          choose a sample from the <strong>offline catalog</strong> below (Google
                          Maps links are disabled in this mode).
                        </>
                      ) : (
                        <>paste a Google Maps link (full or shortened) or a place ID above.</>
                      )}
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center h-6 w-6 rounded-full bg-brand-light text-brand text-xs font-bold shrink-0">
                      2
                    </span>
                    <span>
                      <strong className="text-text-primary">Fetch reviews</strong> — we pull your
                      latest Google reviews automatically.
                    </span>
                  </li>
                  <li className="flex items-start gap-3">
                    <span className="flex items-center justify-center h-6 w-6 rounded-full bg-brand-light text-brand text-xs font-bold shrink-0">
                      3
                    </span>
                    <span>
                      <strong className="text-text-primary">Run analysis</strong> — AI generates a
                      summary, top complaints, praise, action items, and risk areas.
                    </span>
                  </li>
                </ol>
              </div>
            )}
          </div>
        ) : (
          <div className="space-y-6">
            <div className="flex items-end justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-widest text-brand">
                  Workspaces
                </p>
                <h2 className="mt-1 text-xl font-semibold text-text-primary">Continue analysis</h2>
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {sortedBusinesses.map((biz) => (
                <BusinessCard
                  key={biz.id}
                  business={biz}
                  onDelete={handleDelete}
                  deleting={deletingId === biz.id}
                  featured={recommendedBusiness?.id === biz.id}
                />
              ))}
            </div>
            {catalog && (
              <SandboxCatalog
                catalog={catalog}
                onImportPlace={handleImportPlace}
                busyPlaceId={busyPlaceId}
                onResetSandbox={handleResetSandbox}
                resetBusy={resetBusy}
                variant="compact"
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
