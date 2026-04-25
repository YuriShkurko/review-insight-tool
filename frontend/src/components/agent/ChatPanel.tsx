"use client";

import { useEffect, useRef, useCallback } from "react";
import { apiFetch } from "@/lib/api";
import { useAgentChat } from "@/lib/useAgentChat";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { SuggestedPrompts } from "./SuggestedPrompts";

export function ChatPanel({
  businessId,
  onWidgetPinned,
  onCollapse,
}: {
  businessId: string;
  onWidgetPinned: () => void;
  onCollapse?: () => void;
}) {
  const { items, isStreaming, streamingId, error, sendMessage, clearError } = useAgentChat(
    businessId,
    onWidgetPinned,
  );
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items]);

  const handlePin = useCallback(
    async (widgetType: string, title: string, data: Record<string, unknown>) => {
      try {
        await apiFetch(`/businesses/${businessId}/agent/workspace`, {
          method: "POST",
          body: JSON.stringify({ widget_type: widgetType, title, data }),
        });
        onWidgetPinned();
      } catch {
        // silently ignore — user can retry
      }
    },
    [businessId, onWidgetPinned],
  );

  const isEmpty = items.length === 0;

  return (
    <div className="flex flex-col h-full bg-surface-card">
      {/* Chat header */}
      <div className="shrink-0 px-4 py-2.5 border-b border-border flex items-center justify-between">
        <span className="text-sm font-semibold text-text-secondary tracking-wide">Chat</span>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse chat"
            className="text-text-muted hover:text-text-secondary transition-colors p-1 rounded hover:bg-surface-elevated"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <polyline points="9 18 15 12 9 6" />
            </svg>
          </button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {isEmpty ? (
          <SuggestedPrompts onSelect={sendMessage} />
        ) : (
          <div className="space-y-3 max-w-2xl">
            {items.map((item) => (
              <ChatMessage
                key={item.id}
                item={item}
                isStreaming={isStreaming && item.id === streamingId}
                onPin={handlePin}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {error && (
        <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between gap-2 shrink-0 dark:bg-red-950/30 dark:border-red-900 dark:text-red-400">
          <span>{error}</span>
          <button
            type="button"
            onClick={clearError}
            className="shrink-0 text-red-400 hover:text-red-600 transition-colors"
            aria-label="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
