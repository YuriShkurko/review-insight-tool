"use client";

/**
 * Debug-only floating panel.
 * Only mounted when NEXT_PUBLIC_DEBUG_TRAIL=true.
 * Shows a live event trail with copy/download/clear actions.
 */

import { useState, useCallback, useEffect } from "react";
import { getTrail, clearTrail, dumpTrail, type DebugEvent } from "@/lib/debugTrail";

const KIND_COLORS: Record<string, string> = {
  "api:start": "bg-blue-100 text-blue-700",
  "api:ok": "bg-green-100 text-green-700",
  "api:fail": "bg-red-100 text-red-700",
  "auth:login": "bg-purple-100 text-purple-700",
  "auth:logout": "bg-purple-100 text-purple-700",
  "auth:restore": "bg-purple-100 text-purple-700",
  "auth:restore-fail": "bg-red-100 text-red-700",
  "biz:load-start": "bg-sky-100 text-sky-700",
  "biz:load-ok": "bg-green-100 text-green-700",
  "biz:load-fail": "bg-red-100 text-red-700",
  "biz:retry": "bg-amber-100 text-amber-700",
  "route:change": "bg-gray-100 text-gray-600",
  "sandbox:import": "bg-indigo-100 text-indigo-700",
  "sandbox:reset": "bg-orange-100 text-orange-700",
};

function kindColor(kind: string): string {
  return KIND_COLORS[kind] ?? "bg-gray-100 text-gray-600";
}

function relativeTime(ts: number): string {
  const diff = Date.now() - ts;
  if (diff < 1000) return "just now";
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  return `${Math.round(diff / 60_000)}m ago`;
}

function detailSummary(detail?: Record<string, unknown>): string {
  if (!detail) return "";
  return Object.entries(detail)
    .map(([k, v]) => `${k}=${String(v).slice(0, 40)}`)
    .join(" ");
}

export default function DebugPanel() {
  const [open, setOpen] = useState(false);
  const [events, setEvents] = useState<DebugEvent[]>([]);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(() => {
    setEvents([...getTrail()].reverse()); // most recent first
  }, []);

  // Poll every 2s while open; initial refresh is triggered by the toggle button handler
  useEffect(() => {
    if (!open) return;
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [open, refresh]);

  function handleCopy() {
    navigator.clipboard.writeText(dumpTrail()).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  function handleDownload() {
    const blob = new Blob([dumpTrail()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `debug-trail-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function handleClear() {
    clearTrail();
    setEvents([]);
  }

  const count = events.length;

  return (
    <>
      {/* Floating toggle button */}
      <button
        type="button"
        onClick={() => {
          setOpen((o) => !o);
          if (!open) refresh();
        }}
        className="fixed bottom-4 left-4 z-50 text-xs font-mono bg-gray-900 text-green-400 border border-green-700 px-3 py-1.5 rounded-full shadow-lg opacity-80 hover:opacity-100 transition-opacity"
        title="Toggle debug event trail"
      >
        ◉ Debug {open ? "▲" : "▼"}
        {count > 0 && (
          <span className="ml-1 bg-green-700 text-white px-1.5 rounded-full">{count}</span>
        )}
      </button>

      {/* Panel overlay */}
      {open && (
        <div className="fixed bottom-14 left-4 z-50 w-96 max-h-[480px] flex flex-col bg-gray-950 border border-gray-700 rounded-xl shadow-2xl text-xs font-mono overflow-hidden">
          {/* Header */}
          <div className="flex items-center justify-between px-3 py-2 bg-gray-900 border-b border-gray-700 shrink-0">
            <span className="text-green-400 font-semibold tracking-wide">Debug Trail</span>
            <div className="flex gap-1">
              <button
                type="button"
                onClick={refresh}
                className="text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700 transition-colors"
                title="Refresh"
              >
                ↺
              </button>
              <button
                type="button"
                onClick={handleCopy}
                className="text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700 transition-colors"
                title="Copy JSON to clipboard"
              >
                {copied ? "✓" : "Copy"}
              </button>
              <button
                type="button"
                onClick={handleDownload}
                className="text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700 transition-colors"
                title="Download JSON file"
              >
                ↓ Save
              </button>
              <button
                type="button"
                onClick={handleClear}
                className="text-red-400 hover:text-red-300 px-2 py-0.5 rounded hover:bg-gray-700 transition-colors"
                title="Clear trail"
              >
                Clear
              </button>
            </div>
          </div>

          {/* Event list */}
          <div className="overflow-y-auto flex-1">
            {events.length === 0 ? (
              <p className="text-gray-500 text-center py-6">No events yet.</p>
            ) : (
              events.map((ev, i) => (
                <div
                  key={i}
                  className="px-3 py-1.5 border-b border-gray-800 hover:bg-gray-900 transition-colors"
                >
                  <div className="flex items-center gap-2 flex-wrap">
                    <span
                      className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${kindColor(ev.kind)}`}
                    >
                      {ev.kind}
                    </span>
                    <span className="text-gray-500 text-[10px]">{relativeTime(ev.ts)}</span>
                    <span className="text-gray-600 text-[10px] truncate">{ev.route}</span>
                  </div>
                  {ev.detail && (
                    <p className="text-gray-400 mt-0.5 truncate">{detailSummary(ev.detail)}</p>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </>
  );
}
