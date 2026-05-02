"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
import { useAgentChat } from "@/lib/useAgentChat";
import { useWorkspace } from "@/lib/workspaceBlackboard";
import { normalizeWorkspaceWidget } from "@/lib/workspaceWidget";
import { ChatInput } from "./ChatInput";
import { ChatMessage } from "./ChatMessage";
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
    <div className="flex h-full flex-col bg-white">
      <div className="flex shrink-0 items-center justify-between border-b border-slate-200 bg-[#111827] px-4 py-3 text-white">
        <div>
          <p className="text-[10px] font-semibold uppercase tracking-widest text-white/45">
            Copilot
          </p>
          <span className="text-sm font-semibold tracking-wide">Review assistant</span>
        </div>
        {onCollapse && (
          <button
            type="button"
            onClick={onCollapse}
            aria-label="Collapse chat"
            className="rounded p-1 text-white/55 transition-colors hover:bg-white/10 hover:text-white"
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

      <div className="flex-1 overflow-y-auto bg-slate-50 px-4 py-4">
        {isEmpty ? (
          <SuggestedPrompts onSelect={sendMessage} />
        ) : (
          <div className="max-w-2xl space-y-3">
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
        <div className="mx-4 mb-2 flex shrink-0 items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
          <span>{error ?? pinError}</span>
          <button
            type="button"
            onClick={() => {
              clearError();
              setPinError(null);
            }}
            className="shrink-0 text-red-400 transition-colors hover:text-red-600"
            aria-label="Dismiss error"
          >
            x
          </button>
        </div>
      )}

      <ChatInput onSend={sendMessage} disabled={isStreaming} />
    </div>
  );
}
