"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAgentChat } from "@/lib/useAgentChat";
import { useWorkspace } from "@/lib/workspaceBlackboard";
import { normalizeWorkspaceWidget } from "@/lib/workspaceWidget";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { SuggestedPrompts } from "./SuggestedPrompts";
import type { MessageItem, WorkspaceWidget } from "@/lib/agentTypes";

function recoveredPinFailures(items: MessageItem[]): Set<string> {
  const recovered = new Set<string>();
  const failedPins: string[] = [];

  for (const item of items) {
    if (item.kind !== "tool_result" || item.name !== "pin_widget") continue;
    if (item.result?.pinned === true) {
      for (const id of failedPins) recovered.add(id);
      failedPins.length = 0;
    } else if (item.result?.pinned === false) {
      failedPins.push(item.id);
    }
  }

  return recovered;
}

export function ChatPanel({
  businessId,
  onCollapse,
}: {
  businessId: string;
  onCollapse?: () => void;
}) {
  const { dispatch, reload } = useWorkspace();

  const onAgentStreamDone = useCallback(async () => {
    await reload();
  }, [reload]);

  const { items, isStreaming, streamingId, error, sendMessage, clearError } = useAgentChat(
    businessId,
    undefined,
    onAgentStreamDone,
    dispatch,
  );
  const [pinError, setPinError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [items]);

  const handlePin = useCallback(
    async (widgetType: string, title: string, data: Record<string, unknown>) => {
      try {
        const result = await apiFetch<WorkspaceWidget>(
          `/businesses/${businessId}/agent/workspace`,
          {
            method: "POST",
            body: JSON.stringify({ widget_type: widgetType, title, data }),
          },
        );
        setPinError(null);
        dispatch({ type: "WIDGET_ADDED", widget: normalizeWorkspaceWidget(result) });
      } catch {
        setPinError("Failed to pin widget. Please try again.");
      }
    },
    [businessId, dispatch],
  );

  const isEmpty = items.length === 0;
  const recoveredFailures = recoveredPinFailures(items);

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
                isGlobalStreaming={isStreaming}
                isRecovered={recoveredFailures.has(item.id)}
                onPin={handlePin}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {(error || pinError) && (
        <div className="mx-4 mb-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700 flex items-center justify-between gap-2 shrink-0 dark:bg-red-950/30 dark:border-red-900 dark:text-red-400">
          <span>{error ?? pinError}</span>
          <button
            type="button"
            onClick={() => {
              clearError();
              setPinError(null);
            }}
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
