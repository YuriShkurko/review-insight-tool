"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { apiFetch } from "@/lib/api";
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

function humanizeToolName(name: string): string {
  return name.replace(/_/g, " ");
}

export function getAssistantStatus(
  items: MessageItem[],
  isStreaming: boolean,
  hasError: boolean,
): { label: string; detail: string; tone: "idle" | "working" | "done" | "error" } {
  if (hasError) {
    return {
      label: "Needs attention",
      detail: "Review the message below and try again.",
      tone: "error",
    };
  }

  if (isStreaming) {
    const lastTool = [...items].reverse().find((item) => item.kind === "tool_call");
    if (lastTool?.kind === "tool_call") {
      return {
        label: "Working with tools",
        detail: `Running ${humanizeToolName(lastTool.name)}.`,
        tone: "working",
      };
    }
    return {
      label: "Thinking",
      detail: "Reading the workspace and preparing a response.",
      tone: "working",
    };
  }

  if (items.length === 0) {
    return {
      label: "Ready",
      detail: "Ask for a demo dashboard, issue summary, or comparison.",
      tone: "idle",
    };
  }

  return {
    label: "Done",
    detail: "Last action completed. You can keep refining the dashboard.",
    tone: "done",
  };
}

export function getLastActionSummary(items: MessageItem[]): string | null {
  const lastResult = [...items].reverse().find((item) => item.kind === "tool_result");
  if (lastResult?.kind !== "tool_result") return null;

  if (lastResult.name === "pin_widget") {
    return lastResult.result?.pinned === true
      ? "Pinned a widget to the dashboard."
      : "A widget pin did not complete.";
  }
  if (lastResult.name === "clear_dashboard" && lastResult.result?.cleared === true) {
    return "Cleared the dashboard.";
  }
  if (lastResult.name === "remove_widget" && lastResult.result?.removed === true) {
    return "Removed a widget.";
  }
  if (lastResult.name === "duplicate_widget" && lastResult.result?.duplicated === true) {
    return "Copied a widget.";
  }
  if (lastResult.name === "set_dashboard_order" && lastResult.result?.reordered === true) {
    return "Updated dashboard order.";
  }
  if (lastResult.widgetType) {
    return `${humanizeToolName(lastResult.name)} preview is ready.`;
  }
  return null;
}

export interface ChatController {
  items: MessageItem[];
  isStreaming: boolean;
  streamingId: string | null;
  error: string | null;
  sendMessage: (message: string) => void | Promise<void>;
  clearError: () => void;
}

export function ChatPanel({
  businessId,
  chat,
  onCollapse,
}: {
  businessId: string;
  chat: ChatController;
  onCollapse?: () => void;
}) {
  const { dispatch } = useWorkspace();
  const { items, isStreaming, streamingId, error, sendMessage, clearError } = chat;
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
  const assistantStatus = getAssistantStatus(items, isStreaming, Boolean(error || pinError));
  const lastActionSummary = getLastActionSummary(items);

  return (
    <div className="flex h-full flex-col bg-surface-card">
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-[#111827] px-4 py-3 text-white">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-white/45">
            Copilot
          </p>
          <span className="text-sm font-semibold tracking-wide">Review assistant</span>
          <div
            data-testid="assistant-status"
            data-status={assistantStatus.tone}
            className="mt-1 flex min-w-0 items-center gap-2 text-xs text-white/55"
          >
            <span
              className={`h-1.5 w-1.5 shrink-0 rounded-full ${
                assistantStatus.tone === "error"
                  ? "bg-red-300"
                  : assistantStatus.tone === "working"
                    ? "animate-pulse bg-amber-300"
                    : assistantStatus.tone === "done"
                      ? "bg-emerald-300"
                      : "bg-white/35"
              }`}
            />
            <span className="font-medium text-white/75">{assistantStatus.label}</span>
            <span className="truncate">{assistantStatus.detail}</span>
          </div>
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

      <div className="flex-1 overflow-y-auto bg-surface px-4 py-4">
        {isEmpty ? (
          <SuggestedPrompts onSelect={sendMessage} />
        ) : (
          <div className="max-w-2xl space-y-3">
            {lastActionSummary && (
              <div
                data-testid="assistant-last-action"
                className="rounded-lg border border-brand/30 bg-surface-elevated px-3 py-2 text-xs text-text-primary"
              >
                {lastActionSummary}
              </div>
            )}
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
        <div className="mx-4 mb-2 flex shrink-0 items-center justify-between gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800 dark:border-red-900/60 dark:bg-red-950/40 dark:text-red-200">
          <span>{error ?? pinError}</span>
          <button
            type="button"
            onClick={() => {
              clearError();
              setPinError(null);
            }}
            className="shrink-0 text-red-500 transition-colors hover:text-red-700 dark:text-red-300 dark:hover:text-red-100"
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
