"use client";

import { useEffect, useState, useCallback, type FormEvent } from "react";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import { trailEvent } from "@/lib/debugTrail";
import BusinessCard from "@/components/BusinessCard";
import SandboxCatalog from "@/components/SandboxCatalog";
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
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="inline-block h-5 w-5 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold tracking-tight text-text-primary mb-6">Your Businesses</h1>

      {isOfflineDemo ? (
        <div className="mb-4 rounded-lg border border-border bg-surface-elevated px-4 py-3 text-sm text-text-secondary">
          <strong className="text-text-primary">Offline demo mode.</strong> You cannot add a
          business from a Google Maps link or free-form place ID here. Add one from the{" "}
          <strong className="text-text-primary">sample catalog</strong> below instead.
        </div>
      ) : (
        <form onSubmit={handleAdd} className="space-y-2 mb-2">
          <div className="flex gap-2">
            <input
              type="text"
              required
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Paste a Google Maps URL, shortened link, or place ID"
              disabled={adding}
              className="flex-1 border border-border rounded-lg px-3 py-2 text-sm bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand disabled:opacity-50"
            />
            <select
              value={businessType}
              onChange={(e) => setBusinessType(e.target.value as BusinessType)}
              disabled={adding}
              className="border border-border rounded-lg px-3 py-2 text-sm bg-surface text-text-primary focus:outline-none focus:ring-2 focus:ring-brand/30 focus:border-brand disabled:opacity-50 capitalize"
            >
              {BUSINESS_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
            <button
              type="submit"
              disabled={adding || !input.trim()}
              className="bg-brand text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-brand-hover disabled:opacity-50 transition-colors whitespace-nowrap"
            >
              {adding ? "Adding..." : "Add Business"}
            </button>
          </div>
        </form>
      )}

      {error && (
        <p className="text-red-600 text-sm mb-4 bg-red-50 border border-red-200 rounded-lg px-3 py-2 dark:bg-red-950/30 dark:border-red-900 dark:text-red-400">
          {error}
        </p>
      )}
      {!error && <div className="mb-4" />}

      {loadError ? (
        <div className="text-center py-12">
          <p className="text-text-secondary mb-3">{loadError}</p>
          <button
            onClick={() => refreshAll()}
            className="text-brand hover:text-brand-hover text-sm font-medium transition-colors"
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
                        choose a sample from the <strong>offline catalog</strong> below (Google Maps
                        links are disabled in this mode).
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
          <div className="space-y-3">
            {businesses.map((biz) => (
              <BusinessCard
                key={biz.id}
                business={biz}
                onDelete={handleDelete}
                deleting={deletingId === biz.id}
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
  );
}
