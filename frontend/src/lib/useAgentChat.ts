"use client";

import { useReducer, useCallback, useRef } from "react";
import { apiStreamFetch } from "./api";
import type { MessageItem } from "./agentTypes";

interface AgentState {
  items: MessageItem[];
  isStreaming: boolean;
  conversationId: string | null;
  streamingId: string | null;
  error: string | null;
}

type Action =
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

function reducer(state: AgentState, action: Action): AgentState {
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

  // Stable ref so sendMessage doesn't need state in its deps array
  const stateRef = useRef(state);
  stateRef.current = state;

  const sendMessage = useCallback(
    async (message: string) => {
      if (stateRef.current.isStreaming) return;

      dispatch({ type: "ADD_USER", id: crypto.randomUUID(), text: message });

      let res: Response;
      try {
        res = await apiStreamFetch(`/businesses/${businessId}/agent/chat`, {
          method: "POST",
          body: JSON.stringify({
            message,
            conversation_id: stateRef.current.conversationId,
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
      let assistantId = crypto.randomUUID();
      let assistantStarted = false;

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

            if (eventType === "text_delta") {
              if (!assistantStarted) {
                dispatch({ type: "BEGIN_ASSISTANT", id: assistantId });
                assistantStarted = true;
              }
              dispatch({ type: "APPEND_TEXT", id: assistantId, text: data.text as string });
            } else if (eventType === "tool_call") {
              // Next text block after tools needs a fresh assistant item
              assistantId = crypto.randomUUID();
              assistantStarted = false;
              dispatch({
                type: "ADD_TOOL_CALL",
                id: crypto.randomUUID(),
                name: data.name as string,
                args: (data.args ?? {}) as Record<string, unknown>,
              });
            } else if (eventType === "tool_result") {
              const name = data.name as string;
              dispatch({
                type: "ADD_TOOL_RESULT",
                id: crypto.randomUUID(),
                name,
                widgetType: (data.widget_type as string | null) ?? null,
                result: (data.result ?? {}) as Record<string, unknown>,
              });
              if (name === "pin_widget") {
                onWidgetPinned?.();
              }
            } else if (eventType === "done") {
              dispatch({ type: "DONE", conversationId: data.conversation_id as string });
            } else if (eventType === "error") {
              dispatch({
                type: "ERROR",
                message: (data.message as string) || "Something went wrong.",
              });
            }
          }
        }
      } catch {
        dispatch({ type: "ERROR", message: "Stream interrupted. Please try again." });
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
