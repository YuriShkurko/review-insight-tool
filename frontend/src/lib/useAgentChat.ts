"use client";

import { useReducer, useCallback, useEffect, useRef, useState } from "react";
import { apiFetch, ApiError, apiStreamFetch } from "./api";
import type { ConversationDetail, MessageItem, WorkspaceWidget } from "./agentTypes";
import type { WorkspaceAction } from "./workspaceBlackboard";
import { normalizeWorkspaceWidget } from "./workspaceWidget";

export interface AgentState {
  items: MessageItem[];
  isStreaming: boolean;
  conversationId: string | null;
  streamingId: string | null;
  error: string | null;
}

export type Action =
  | { type: "ADD_USER"; id: string; text: string }
  | { type: "BEGIN_ASSISTANT"; id: string }
  | { type: "APPEND_TEXT"; id: string; text: string }
  | { type: "ADD_TOOL_CALL"; id: string; name: string; args: Record<string, unknown> }
  | {
      type: "ADD_TOOL_RESULT";
      id: string;
      name: string;
      widgetType: string | null;
      result: Record<string, unknown>;
    }
  | { type: "SEED_HISTORY"; items: MessageItem[]; conversationId: string }
  | { type: "DONE"; conversationId: string }
  | { type: "ERROR"; message: string }
  | { type: "CLEAR_ERROR" };

export function shouldTriggerWidgetPinned(name: string, result: Record<string, unknown>): boolean {
  return name === "pin_widget" && result?.pinned === true;
}

export function dispatchWorkspaceEvent(
  data: Record<string, unknown>,
  workspaceDispatch?: (action: WorkspaceAction) => void,
): void {
  const action = data.action as string;
  if (action === "widget_added" && data.widget && workspaceDispatch) {
    workspaceDispatch({
      type: "WIDGET_ADDED",
      widget: normalizeWorkspaceWidget(data.widget) as WorkspaceWidget,
    });
  } else if (action === "widget_removed" && data.widget_id && workspaceDispatch) {
    workspaceDispatch({ type: "WIDGET_REMOVED", widgetId: String(data.widget_id) });
  } else if (
    action === "widgets_reordered" &&
    Array.isArray(data.widget_ids) &&
    workspaceDispatch
  ) {
    workspaceDispatch({ type: "WIDGET_REORDERED", widgetIds: data.widget_ids.map(String) });
  }
}

function createClientId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }

  return `msg_${Date.now().toString(36)}_${Math.random().toString(36).slice(2)}`;
}

export function reducer(state: AgentState, action: Action): AgentState {
  switch (action.type) {
    case "ADD_USER":
      return {
        ...state,
        items: [...state.items, { id: action.id, kind: "user", text: action.text }],
        isStreaming: true,
        error: null,
      };
    case "BEGIN_ASSISTANT":
      return {
        ...state,
        items: [...state.items, { id: action.id, kind: "assistant_text", text: "" }],
        streamingId: action.id,
      };
    case "APPEND_TEXT":
      return {
        ...state,
        items: state.items.map((item) =>
          item.id === action.id && item.kind === "assistant_text"
            ? { ...item, text: item.text + action.text }
            : item,
        ),
      };
    case "ADD_TOOL_CALL":
      return {
        ...state,
        items: [
          ...state.items,
          { id: action.id, kind: "tool_call", name: action.name, args: action.args },
        ],
        streamingId: null,
      };
    case "ADD_TOOL_RESULT":
      return {
        ...state,
        items: [
          ...state.items,
          {
            id: action.id,
            kind: "tool_result",
            name: action.name,
            widgetType: action.widgetType,
            result: action.result,
          },
        ],
      };
    case "SEED_HISTORY":
      return {
        ...state,
        items: action.items,
        isStreaming: false,
        streamingId: null,
        conversationId: action.conversationId,
        error: null,
      };
    case "DONE":
      return {
        ...state,
        isStreaming: false,
        streamingId: null,
        conversationId: action.conversationId,
      };
    case "ERROR":
      return { ...state, isStreaming: false, streamingId: null, error: action.message };
    case "CLEAR_ERROR":
      return { ...state, error: null };
    default:
      return state;
  }
}

/**
 * @param onWidgetPinned — called when the agent's pin_widget tool returns pinned: true (e.g. toast).
 * @param onAgentStreamDone — called when the SSE stream ends with a successful `done` event;
 *   fires a safety-net workspace reload to reconcile blackboard state with the server.
 * @param workspaceDispatch — blackboard dispatch; workspace_event SSE → WIDGET_ADDED.
 */
export function useAgentChat(
  businessId: string,
  onWidgetPinned?: () => void,
  onAgentStreamDone?: () => void | Promise<void>,
  workspaceDispatch?: (action: WorkspaceAction) => void,
) {
  const [storedConversationId] = useState(() => {
    if (typeof window === "undefined") return null;
    return localStorage.getItem(`conv_${businessId}`);
  });
  const [state, dispatch] = useReducer(reducer, {
    items: [],
    isStreaming: false,
    conversationId: storedConversationId,
    streamingId: null,
    error: null,
  });

  // Refs updated synchronously in sendMessage — no useEffect timing window.
  // isStreamingRef guards against concurrent calls without relying on React state
  // being visible before the next render. conversationIdRef keeps the latest
  // conversation ID available in the sendMessage closure without needing it in deps.
  const isStreamingRef = useRef(false);
  const conversationIdRef = useRef<string | null>(storedConversationId);

  useEffect(() => {
    if (!storedConversationId) return;
    let cancelled = false;

    async function loadHistory() {
      try {
        const conversation = await apiFetch<ConversationDetail>(
          `/businesses/${businessId}/agent/conversations/${storedConversationId}`,
        );
        if (cancelled) return;
        const items = conversation.messages
          .filter(
            (message) =>
              (message.role === "user" || message.role === "assistant") &&
              typeof message.content === "string" &&
              message.content.trim().length > 0,
          )
          .map((message) => ({
            id: createClientId(),
            kind: message.role === "user" ? "user" : "assistant_text",
            text: message.content as string,
          })) as MessageItem[];
        dispatch({ type: "SEED_HISTORY", items, conversationId: conversation.id });
        conversationIdRef.current = conversation.id;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return;
      }
    }

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [businessId, storedConversationId]);

  const sendMessage = useCallback(
    async (message: string) => {
      if (isStreamingRef.current) return;
      isStreamingRef.current = true;

      dispatch({ type: "ADD_USER", id: createClientId(), text: message });

      try {
        let res: Response;
        try {
          res = await apiStreamFetch(`/businesses/${businessId}/agent/chat`, {
            method: "POST",
            body: JSON.stringify({
              message,
              conversation_id: conversationIdRef.current,
            }),
          });
        } catch {
          dispatch({ type: "ERROR", message: "Network error. Please check your connection." });
          return;
        }

        if (!res.ok) {
          dispatch({ type: "ERROR", message: "Request failed. Please try again." });
          return;
        }

        const reader = res.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let assistantId = createClientId();
        let assistantStarted = false;
        let streamCompleted = false;

        try {
          while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            buffer += decoder.decode(value, { stream: true });

            const blocks = buffer.split("\n\n");
            buffer = blocks.pop() ?? "";

            for (const block of blocks) {
              if (!block.trim()) continue;
              const lines = block.split("\n");
              let eventType = "message";
              let dataStr = "";
              for (const line of lines) {
                if (line.startsWith("event: ")) eventType = line.slice(7).trim();
                else if (line.startsWith("data: ")) dataStr = line.slice(6);
              }
              if (!dataStr) continue;

              let data: Record<string, unknown>;
              try {
                data = JSON.parse(dataStr);
              } catch {
                continue;
              }

              if (eventType === "status") {
                // Keep-alive ping from backend — no state change needed
              } else if (eventType === "text_delta") {
                if (!assistantStarted) {
                  dispatch({ type: "BEGIN_ASSISTANT", id: assistantId });
                  assistantStarted = true;
                }
                dispatch({ type: "APPEND_TEXT", id: assistantId, text: data.text as string });
              } else if (eventType === "tool_call") {
                assistantId = createClientId();
                assistantStarted = false;
                dispatch({
                  type: "ADD_TOOL_CALL",
                  id: createClientId(),
                  name: data.name as string,
                  args: (data.args ?? {}) as Record<string, unknown>,
                });
              } else if (eventType === "tool_result") {
                const name = data.name as string;
                dispatch({
                  type: "ADD_TOOL_RESULT",
                  id: createClientId(),
                  name,
                  widgetType: (data.widget_type as string | null) ?? null,
                  result: (data.result ?? {}) as Record<string, unknown>,
                });
                if (
                  shouldTriggerWidgetPinned(name, (data.result as Record<string, unknown>) ?? {})
                ) {
                  onWidgetPinned?.();
                }
              } else if (eventType === "workspace_event") {
                dispatchWorkspaceEvent(data, workspaceDispatch);
              } else if (eventType === "done") {
                const conversationId = (data.conversation_id as string) ?? "";
                conversationIdRef.current = conversationId || null;
                if (conversationId && typeof window !== "undefined") {
                  localStorage.setItem(`conv_${businessId}`, conversationId);
                }
                dispatch({ type: "DONE", conversationId });
                streamCompleted = true;
                void Promise.resolve(onAgentStreamDone?.());
              } else if (eventType === "error") {
                dispatch({
                  type: "ERROR",
                  message: (data.message as string) || "Something went wrong.",
                });
                streamCompleted = true;
                void Promise.resolve(onAgentStreamDone?.());
              }
            }
          }
        } catch {
          dispatch({ type: "ERROR", message: "Stream interrupted. Please try again." });
          void Promise.resolve(onAgentStreamDone?.());
          return;
        }

        if (!streamCompleted) {
          dispatch({
            type: "ERROR",
            message: "Response ended unexpectedly. Please try again.",
          });
          void Promise.resolve(onAgentStreamDone?.());
        }
      } finally {
        isStreamingRef.current = false;
      }
    },
    [businessId, onWidgetPinned, onAgentStreamDone, workspaceDispatch],
  );

  const clearError = useCallback(() => dispatch({ type: "CLEAR_ERROR" }), []);

  return {
    items: state.items,
    isStreaming: state.isStreaming,
    streamingId: state.streamingId,
    conversationId: state.conversationId,
    error: state.error,
    sendMessage,
    clearError,
  };
}
