"use client";

import { useState } from "react";
import type { Review } from "@/lib/types";

const PREVIEW_COUNT = 5;

export default function ReviewList({ reviews }: { reviews: Review[] }) {
  const [expanded, setExpanded] = useState(false);

  if (reviews.length === 0) return null;

  const visible = expanded ? reviews : reviews.slice(0, PREVIEW_COUNT);

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-5">
      <h3 className="font-semibold text-sm text-gray-500 uppercase tracking-wide mb-3">
        Reviews ({reviews.length})
      </h3>
      <div className="space-y-3">
        {visible.map((r) => (
          <div
            key={r.id}
            className="border-b border-gray-100 pb-3 last:border-0"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-sm font-medium">
                {r.author || "Anonymous"}
              </span>
              <span className="text-sm text-yellow-600 font-medium">
                {"★".repeat(Math.min(r.rating, 5))}
                {"☆".repeat(Math.max(5 - r.rating, 0))}
              </span>
            </div>
            {r.text && (
              <p className="text-sm text-gray-700 leading-relaxed">{r.text}</p>
            )}
          </div>
        ))}
      </div>
      {reviews.length > PREVIEW_COUNT && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-sm text-blue-600 hover:underline"
        >
          {expanded ? "Show less" : `Show all ${reviews.length} reviews`}
        </button>
      )}
    </div>
  );
}
