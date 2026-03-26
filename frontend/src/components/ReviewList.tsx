"use client";

import { useState } from "react";
import type { Review } from "@/lib/types";

const PREVIEW_COUNT = 5;
const HEBREW_RE = /[\u0590-\u05FF]/g;
const MOJIBAKE_HINT_RE = /(Ã|Â|Î|ð|�)/;

function hebrewScore(value: string): number {
  return (value.match(HEBREW_RE) ?? []).length;
}

function repairMojibake(value: string | null | undefined): string {
  if (!value) return "";
  if (!MOJIBAKE_HINT_RE.test(value)) return value;

  try {
    const bytes = Uint8Array.from(Array.from(value).map((ch) => ch.charCodeAt(0) & 0xff));
    const decoded = new TextDecoder("utf-8").decode(bytes);
    return hebrewScore(decoded) > hebrewScore(value) ? decoded : value;
  } catch {
    return value;
  }
}

function StarRating({ rating }: { rating: number }) {
  const clamped = Math.min(Math.max(rating, 0), 5);
  return (
    <span className="text-sm font-medium text-amber-500 tracking-tight">
      {"★".repeat(clamped)}
      {"☆".repeat(5 - clamped)}
    </span>
  );
}

export default function ReviewList({ reviews }: { reviews: Review[] }) {
  const [expanded, setExpanded] = useState(false);

  if (reviews.length === 0) return null;

  const visible = expanded ? reviews : reviews.slice(0, PREVIEW_COUNT);

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-5">
      <div className="space-y-3">
        {visible.map((r) => (
          <div key={r.id} className="border-b border-gray-100 pb-3 last:border-0 last:pb-0">
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium text-gray-800">
                {repairMojibake(r.author) || "Anonymous"}
              </span>
              <StarRating rating={r.rating} />
            </div>
            {r.text && (
              <p className="text-sm text-gray-600 leading-relaxed" dir="auto">
                {repairMojibake(r.text)}
              </p>
            )}
          </div>
        ))}
      </div>
      {reviews.length > PREVIEW_COUNT && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-4 text-sm text-blue-600 hover:text-blue-700 font-medium"
        >
          {expanded ? "Show fewer" : `Show all ${reviews.length} reviews`}
        </button>
      )}
    </div>
  );
}
