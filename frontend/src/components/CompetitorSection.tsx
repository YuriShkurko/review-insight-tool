"use client";

import { useEffect, useState, useCallback, type FormEvent } from "react";
import Link from "next/link";
import { apiFetch, ApiError } from "@/lib/api";
import {
  BUSINESS_TYPES,
  type CompetitorRead,
  type BusinessType,
} from "@/lib/types";

const MAX_COMPETITORS = 3;

export default function CompetitorSection({
  businessId,
  onCompetitorsChange,
}: {
  businessId: string;
  onCompetitorsChange?: (competitors: CompetitorRead[]) => void;
}) {
  const [competitors, setCompetitors] = useState<CompetitorRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [removing, setRemoving] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [input, setInput] = useState("");
  const [businessType, setBusinessType] = useState<BusinessType>("other");

  const loadCompetitors = useCallback(async () => {
    try {
      const data = await apiFetch<CompetitorRead[]>(
        `/businesses/${businessId}/competitors`
      );
      setCompetitors(data);
      onCompetitorsChange?.(data);
    } catch {
      setCompetitors([]);
      onCompetitorsChange?.([]);
    } finally {
      setLoading(false);
    }
  }, [businessId, onCompetitorsChange]);

  useEffect(() => {
    loadCompetitors();
  }, [loadCompetitors]);

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
      await apiFetch<CompetitorRead>(
        `/businesses/${businessId}/competitors`,
        { method: "POST", body: JSON.stringify(body) }
      );
      await loadCompetitors();
      setInput("");
      setBusinessType("other");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to add competitor."
      );
    } finally {
      setAdding(false);
    }
  }

  async function handleRemove(competitorBusinessId: string) {
    setError("");
    setRemoving(competitorBusinessId);
    try {
      await apiFetch(
        `/businesses/${businessId}/competitors/${competitorBusinessId}`,
        { method: "DELETE" }
      );
      await loadCompetitors();
    } catch (err) {
      setError(
        err instanceof ApiError ? err.detail : "Failed to remove competitor."
      );
    } finally {
      setRemoving(null);
    }
  }

  if (loading) {
    return (
      <div className="bg-white border border-gray-200 rounded-lg p-5">
        <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">
          Competitors
        </h3>
        <div className="text-sm text-gray-500">Loading…</div>
      </div>
    );
  }

  const atLimit = competitors.length >= MAX_COMPETITORS;

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">
        Competitors
      </h3>
      <p className="text-sm text-gray-600 mb-4">
        Add up to {MAX_COMPETITORS} competitor businesses to compare insights.
        Open each competitor to fetch reviews and run analysis.
      </p>

      {!atLimit && (
        <form onSubmit={handleAdd} className="space-y-2 mb-4">
          <div className="flex flex-wrap gap-2 items-end">
            <div className="flex-1 min-w-[200px]">
              <label className="block text-xs text-gray-500 mb-1">
                Google Maps URL, shortened link, or place ID
              </label>
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="https://maps.app.goo.gl/... or full Maps URL"
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm"
              />
            </div>
            <div className="w-32">
              <label className="block text-xs text-gray-500 mb-1">Type</label>
              <select
                value={businessType}
                onChange={(e) => setBusinessType(e.target.value as BusinessType)}
                className="w-full border border-gray-300 rounded px-3 py-2 text-sm capitalize"
              >
                {BUSINESS_TYPES.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
            <button
              type="submit"
              disabled={adding || !input.trim()}
              className="bg-blue-600 text-white px-4 py-2 rounded text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {adding ? "Adding…" : "Add Competitor"}
            </button>
          </div>
        </form>
      )}

      {error && (
        <p className="text-red-600 text-sm bg-red-50 border border-red-200 rounded px-3 py-2 mb-4">
          {error}
        </p>
      )}

      {competitors.length === 0 ? (
        <p className="text-sm text-gray-500">No competitors linked yet.</p>
      ) : (
        <ul className="space-y-2">
          {competitors.map(({ link_id, business, has_reviews, has_analysis }) => (
            <li
              key={link_id}
              className="flex items-center justify-between gap-2 py-2 border-b border-gray-100 last:border-0"
            >
              <Link
                href={`/businesses/${business.id}`}
                className="flex-1 min-w-0 font-medium text-blue-600 hover:underline truncate"
              >
                {business.name}
              </Link>
              <span className="text-sm text-gray-500 shrink-0">
                {business.avg_rating != null
                  ? `★ ${business.avg_rating.toFixed(1)}`
                  : "—"}{" "}
                · {business.total_reviews} reviews
              </span>
              {has_analysis ? (
                <span className="text-xs bg-green-100 text-green-700 px-2 py-0.5 rounded-full shrink-0">
                  Analyzed
                </span>
              ) : has_reviews ? (
                <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full shrink-0">
                  Needs analysis
                </span>
              ) : (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded-full shrink-0">
                  Needs reviews
                </span>
              )}
              <button
                type="button"
                onClick={() => handleRemove(business.id)}
                disabled={removing === business.id}
                className="text-red-600 text-sm hover:underline disabled:opacity-50 shrink-0"
              >
                {removing === business.id ? "Removing…" : "Remove"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
