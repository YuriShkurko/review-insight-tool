"use client";

import { useRef, useState, useEffect, useCallback } from "react";

interface ResizablePanelProps {
  left: React.ReactNode;
  right: React.ReactNode;
  defaultRatio?: number;
  minLeft?: number;
  maxLeft?: number;
  storageKey?: string;
  rightCollapsed?: boolean;
  onRightCollapsedChange?: (collapsed: boolean) => void;
}

export function ResizablePanel({
  left,
  right,
  defaultRatio = 0.65,
  minLeft = 0.4,
  maxLeft = 0.85,
  storageKey = "panel-split",
  rightCollapsed = false,
  onRightCollapsedChange,
}: ResizablePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [ratio, setRatio] = useState(() => {
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = parseFloat(stored);
        if (parsed >= minLeft && parsed <= maxLeft) return parsed;
      }
    } catch {}
    return defaultRatio;
  });
  const isDragging = useRef(false);

  const onMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    isDragging.current = true;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  }, []);

  useEffect(() => {
    function onMouseMove(e: MouseEvent) {
      if (!isDragging.current || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const newRatio = (e.clientX - rect.left) / rect.width;
      const clamped = Math.min(Math.max(newRatio, minLeft), maxLeft);
      setRatio(clamped);
    }

    function onMouseUp() {
      if (!isDragging.current) return;
      isDragging.current = false;
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      setRatio((r) => {
        try { localStorage.setItem(storageKey, String(r)); } catch {}
        return r;
      });
    }

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [storageKey, minLeft, maxLeft]);

  const leftPct = rightCollapsed ? 100 : ratio * 100;
  const rightPct = rightCollapsed ? 0 : (1 - ratio) * 100;

  return (
    <div ref={containerRef} className="flex-1 flex overflow-hidden relative">
      {/* Left panel */}
      <div
        style={{ width: `${leftPct}%` }}
        className="h-full overflow-hidden transition-[width] duration-300"
      >
        {left}
      </div>

      {/* Drag handle */}
      {!rightCollapsed && (
        <div
          onMouseDown={onMouseDown}
          className="shrink-0 w-1 cursor-col-resize group flex items-center justify-center hover:bg-border transition-colors z-10"
          title="Drag to resize"
        >
          <div className="w-0.5 h-8 rounded-full bg-border group-hover:bg-text-muted transition-colors" />
        </div>
      )}

      {/* Right panel */}
      <div
        style={{ width: `${rightPct}%` }}
        className="h-full overflow-hidden transition-[width] duration-300"
      >
        {!rightCollapsed && right}
      </div>

      {/* Collapsed chat pill */}
      {rightCollapsed && onRightCollapsedChange && (
        <button
          onClick={() => onRightCollapsedChange(false)}
          className="absolute bottom-6 right-6 z-20 flex items-center gap-2 bg-brand text-white px-4 py-2 rounded-full shadow-lg text-sm font-medium hover:bg-brand-hover transition-colors"
        >
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Open Chat
        </button>
      )}
    </div>
  );
}
