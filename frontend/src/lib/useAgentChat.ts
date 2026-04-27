"use client";

import { useReducer, useCallback, useRef } from "react";
import { apiStreamFetch } from "./api";
import type { MessageItem } from "./agentTypes";

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
  | { type: "DONE"; conversationId: string }
  | { type: "ERROR"; message: string }
  | { type: "CLEAR_ERROR" };

export function shouldTriggerWidgetPinned(name: string, result: Record<string, unknown>): boolean {
  return name === "pin_widget" && result?.pinned === true;
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

export function useAgentChat(businessId: string, onWidgetPinned?: () => void) {
  const [state, dispatch] = useReducer(reducer, {
    items: [],
    isStreaming: false,
    conversationId: null,
    streamingId: null,
    error: null,
  });

  // Refs updated synchronously in sendMessage — no useEffect timing window.
  // isStreamingRef guards against concurrent calls without relying on React state
  // being visible before the next render. conversationIdRef keeps the latest
  // conversation ID available in the sendMessage closure without needing it in deps.
  const isStreamingRef = useRef(false);
  const conversationIdRef = useRef<string | null>(null);

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
              } else if (eventType === "done") {
                const conversationId = data.conversation_id as string;
                conversationIdRef.current = conversationId;
                dispatch({ type: "DONE", conversationId });
                streamCompleted = true;
              } else if (eventType === "error") {
                dispatch({
                  type: "ERROR",
                  message: (data.message as string) || "Something went wrong.",
                });
                streamCompleted = true;
              }
            }
          }
        } catch {
          dispatch({ type: "ERROR", message: "Stream interrupted. Please try again." });
          return;
        }

        if (!streamCompleted) {
          dispatch({
            type: "ERROR",
            message: "Response ended unexpectedly. Please try again.",
          });
        }
      } finally {
        isStreamingRef.current = false;
      }
    },
    [businessId, onWidgetPinned],
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
