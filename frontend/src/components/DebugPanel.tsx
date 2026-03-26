"use client";

/**
 * Debug-only floating panel.
 * Only mounted when NEXT_PUBLIC_DEBUG_TRAIL=true.
 * Shows a live event trail with copy/download/clear actions.
 */

import { useState, useCallback, useEffect } from "react";
import { getTrail, clearTrail, dumpTrail, type DebugEvent } from "@/lib/debugTrail";
import { getSelected, clearSelection, type ElementNode } from "@/lib/debugSelector";

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

type Tab = "trail" | "selector";

export default function DebugPanel() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<Tab>("trail");
  const [events, setEvents] = useState<DebugEvent[]>([]);
  const [selected, setSelected] = useState<ElementNode[]>([]);
  const [copied, setCopied] = useState(false);

  const refresh = useCallback(() => {
    setEvents([...getTrail()].reverse()); // most recent first
    setSelected([...getSelected()]);
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

  function handleClearSelection() {
    clearSelection();
    setSelected([]);
  }

  const count = events.length;

  return (
    <>
      {/* Floating toggle button */}
      <button
        type="button"
        data-debug-panel
        onClick={() => {
          setOpen((o) => !o);
          if (!open) refresh();
        }}
        className="fixed bottom-4 left-4 z-50 text-xs font-mono bg-gray-900 text-green-400 border border-green-700 px-3 py-1.5 rounded-full shadow-lg opacity-80 hover:opacity-100 transition-opacity"
        title="Toggle debug panel"
      >
        ◉ Debug {open ? "▲" : "▼"}
        {count > 0 && (
          <span className="ml-1 bg-green-700 text-white px-1.5 rounded-full">{count}</span>
        )}
        {selected.length > 0 && (
          <span className="ml-1 bg-purple-700 text-white px-1.5 rounded-full">{selected.length}⬡</span>
        )}
      </button>

      {/* Panel overlay */}
      {open && (
        <div data-debug-panel className="fixed bottom-14 left-4 z-50 w-[420px] max-h-[520px] flex flex-col bg-gray-950 border border-gray-700 rounded-xl shadow-2xl text-xs font-mono overflow-hidden">
          {/* Tabs */}
          <div className="flex items-center border-b border-gray-700 shrink-0 bg-gray-900">
            <button
              type="button"
              onClick={() => setTab("trail")}
              className={`px-3 py-2 font-semibold tracking-wide transition-colors ${tab === "trail" ? "text-green-400 border-b-2 border-green-500" : "text-gray-500 hover:text-gray-300"}`}
            >
              Trail {count > 0 && <span className="ml-1 text-[10px] text-green-600">{count}</span>}
            </button>
            <button
              type="button"
              onClick={() => setTab("selector")}
              className={`px-3 py-2 font-semibold tracking-wide transition-colors ${tab === "selector" ? "text-purple-400 border-b-2 border-purple-500" : "text-gray-500 hover:text-gray-300"}`}
            >
              Selector {selected.length > 0 && <span className="ml-1 text-[10px] text-purple-400">{selected.length}</span>}
            </button>
            <div className="ml-auto flex gap-1 pr-2">
              <button type="button" onClick={refresh} className="text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700" title="Refresh">↺</button>
              {tab === "trail" && <>
                <button type="button" onClick={handleCopy} className="text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700">{copied ? "✓" : "Copy"}</button>
                <button type="button" onClick={handleDownload} className="text-gray-400 hover:text-white px-2 py-0.5 rounded hover:bg-gray-700">↓</button>
                <button type="button" onClick={handleClear} className="text-red-400 hover:text-red-300 px-2 py-0.5 rounded hover:bg-gray-700">Clear</button>
              </>}
              {tab === "selector" && selected.length > 0 && (
                <button type="button" onClick={handleClearSelection} className="text-red-400 hover:text-red-300 px-2 py-0.5 rounded hover:bg-gray-700">Clear</button>
              )}
            </div>
          </div>

          {/* Trail tab */}
          {tab === "trail" && (
            <div className="overflow-y-auto flex-1">
              {events.length === 0 ? (
                <p className="text-gray-500 text-center py-6">No events yet.</p>
              ) : (
                events.map((ev, i) => (
                  <div key={i} className="px-3 py-1.5 border-b border-gray-800 hover:bg-gray-900 transition-colors">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className={`px-1.5 py-0.5 rounded text-[10px] font-semibold ${kindColor(ev.kind)}`}>{ev.kind}</span>
                      <span className="text-gray-500 text-[10px]">{relativeTime(ev.ts)}</span>
                      <span className="text-gray-600 text-[10px] truncate">{ev.route}</span>
                    </div>
                    {ev.detail && <p className="text-gray-400 mt-0.5 truncate">{detailSummary(ev.detail)}</p>}
                  </div>
                ))
              )}
            </div>
          )}

          {/* Selector tab */}
          {tab === "selector" && (
            <div className="overflow-y-auto flex-1">
              {selected.length === 0 ? (
                <div className="text-gray-500 text-center py-6 px-4 leading-relaxed">
                  <p className="text-purple-400 font-semibold mb-1">Element Selector</p>
                  <p>Hold <kbd className="bg-gray-800 text-gray-300 px-1 rounded">CTRL</kbd> and click any element to inspect it.</p>
                  <p className="mt-1 text-[10px]">Double-tap CTRL to deselect all.</p>
                </div>
              ) : (
                selected.map((el, i) => (
                  <div key={i} className="px-3 py-2 border-b border-gray-800">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-purple-400 font-semibold">&lt;{el.tag}&gt;</span>
                      {el.reactComponent && (
                        <span className="text-fuchsia-400 text-[10px] bg-fuchsia-950 px-1.5 rounded">⚛ {el.reactComponent}</span>
                      )}
                      {el.id && <span className="text-gray-400 text-[10px]">#{el.id}</span>}
                    </div>
                    <p className="text-gray-500 text-[10px] truncate mb-1">{el.path}</p>
                    {el.text && (
                      <p className="text-gray-400 text-[10px] truncate italic">"{el.text.slice(0, 80)}"</p>
                    )}
                    <div className="flex gap-3 mt-1 text-[10px] text-gray-600">
                      <span>{el.rect.width}×{el.rect.height}</span>
                      <span>({el.rect.x}, {el.rect.y})</span>
                      {el.children.length > 0 && <span>{el.children.length} children</span>}
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}
    </>
  );
}
