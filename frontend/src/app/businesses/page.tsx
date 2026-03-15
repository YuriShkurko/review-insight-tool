"use client";

import { useEffect, useState, useCallback, type FormEvent } from "react";
import { useRequireAuth } from "@/lib/auth";
import { apiFetch, ApiError } from "@/lib/api";
import BusinessCard from "@/components/BusinessCard";
import { BUSINESS_TYPES, type Business, type BusinessType } from "@/lib/types";

export default function BusinessesPage() {
  const { user, isLoading } = useRequireAuth();
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [loading, setLoading] = useState(true);
  const [input, setInput] = useState("");
  const [businessType, setBusinessType] = useState<BusinessType>("other");
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState("");
  const [loadError, setLoadError] = useState("");

  const loadBusinesses = useCallback(async () => {
    try {
      setLoadError("");
      const data = await apiFetch<Business[]>("/businesses");
      setBusinesses(data);
    } catch {
      setLoadError("Could not load your businesses. Please try refreshing.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user) return;
    loadBusinesses();
  }, [user, loadBusinesses]);

  async function handleAdd(e: FormEvent) {
    e.preventDefault();
    setError("");
    setAdding(true);

    const trimmed = input.trim();
    const isUrl = trimmed.startsWith("http");
    const body = isUrl
      ? { google_maps_url: trimmed, place_id: null, business_type: businessType }
      : { place_id: trimmed, google_maps_url: null, business_type: businessType };

    try {
      const biz = await apiFetch<Business>("/businesses", {
        method: "POST",
        body: JSON.stringify(body),
      });
      setBusinesses((prev) => [biz, ...prev]);
      setInput("");
      setBusinessType("other");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to add business."
      );
    } finally {
      setAdding(false);
    }
  }

  if (isLoading || loading) {
    return (
      <div className="flex justify-center items-center min-h-[50vh]">
        <div className="inline-block h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold tracking-tight mb-6">Your Businesses</h1>

      <form onSubmit={handleAdd} className="space-y-2 mb-2">
        <div className="flex gap-2">
          <input
            type="text"
            required
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Paste a Google Maps URL, shortened link, or place ID"
            disabled={adding}
            className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50"
          />
          <select
            value={businessType}
            onChange={(e) => setBusinessType(e.target.value as BusinessType)}
            disabled={adding}
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 capitalize"
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
            className="bg-blue-600 text-white px-5 py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors whitespace-nowrap"
          >
            {adding ? "Adding..." : "Add Business"}
          </button>
        </div>
      </form>

      {error && (
        <p className="text-red-600 text-sm mb-4 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {error}
        </p>
      )}
      {!error && <div className="mb-4" />}

      {loadError ? (
        <div className="text-center py-12">
          <p className="text-gray-500 mb-3">{loadError}</p>
          <button
            onClick={loadBusinesses}
            className="text-blue-600 hover:underline text-sm font-medium"
          >
            Retry
          </button>
        </div>
      ) : businesses.length === 0 ? (
        <div className="bg-white border border-gray-200 rounded-xl p-8">
          <h2 className="text-lg font-semibold text-gray-800 mb-1">
            Welcome to Review Insight
          </h2>
          <p className="text-gray-500 text-sm mb-5">
            Understand what your customers are saying — in three simple steps.
          </p>
          <ol className="space-y-3 text-sm text-gray-700">
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0">
                1
              </span>
              <span>
                <strong>Add your business</strong> — paste a Google Maps link
                (full or shortened) or a place ID above.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0">
                2
              </span>
              <span>
                <strong>Fetch reviews</strong> — we pull your latest Google reviews automatically.
              </span>
            </li>
            <li className="flex items-start gap-3">
              <span className="flex items-center justify-center h-6 w-6 rounded-full bg-blue-100 text-blue-700 text-xs font-bold shrink-0">
                3
              </span>
              <span>
                <strong>Run analysis</strong> — AI generates a summary,
                top complaints, praise, action items, and risk areas.
              </span>
            </li>
          </ol>
        </div>
      ) : (
        <div className="space-y-3">
          {businesses.map((biz) => (
            <BusinessCard key={biz.id} business={biz} />
          ))}
        </div>
      )}
    </div>
  );
}
