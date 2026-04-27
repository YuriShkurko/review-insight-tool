/**
 * Unit tests for the useAgentChat reducer — pure state transitions.
 *
 * These tests verify that the streaming spinner state (isStreaming, streamingId)
 * is always cleared on DONE, ERROR, and that ADD_TOOL_CALL resets the assistant
 * streaming cursor.
 */

import { describe, it, expect } from "vitest";
import { reducer, type AgentState } from "../useAgentChat";

const INITIAL: AgentState = {
  items: [],
  isStreaming: false,
  conversationId: null,
  streamingId: null,
  error: null,
};

describe("useAgentChat reducer", () => {
  it("ADD_USER sets isStreaming: true and clears error", () => {
    const state = reducer(
      { ...INITIAL, error: "previous error" },
      { type: "ADD_USER", id: "u1", text: "hello" },
    );
    expect(state.isStreaming).toBe(true);
    expect(state.error).toBeNull();
    expect(state.items).toHaveLength(1);
    expect(state.items[0]).toMatchObject({ kind: "user", text: "hello" });
  });

  it("DONE sets isStreaming: false and streamingId: null", () => {
    let state = reducer(INITIAL, { type: "ADD_USER", id: "u1", text: "hi" });
    state = reducer(state, { type: "BEGIN_ASSISTANT", id: "a1" });
    expect(state.isStreaming).toBe(true);
    expect(state.streamingId).toBe("a1");

    state = reducer(state, { type: "DONE", conversationId: "conv-1" });
    expect(state.isStreaming).toBe(false);
    expect(state.streamingId).toBeNull();
    expect(state.conversationId).toBe("conv-1");
  });

  it("ERROR sets isStreaming: false, streamingId: null, and populates error", () => {
    const streaming: AgentState = {
      ...INITIAL,
      isStreaming: true,
      streamingId: "msg-1",
    };
    const state = reducer(streaming, { type: "ERROR", message: "Network failure" });
    expect(state.isStreaming).toBe(false);
    expect(state.streamingId).toBeNull();
    expect(state.error).toBe("Network failure");
  });

  it("ADD_TOOL_CALL clears streamingId (ends assistant text cursor)", () => {
    const withStreaming: AgentState = { ...INITIAL, streamingId: "msg-1" };
    const state = reducer(withStreaming, {
      type: "ADD_TOOL_CALL",
      id: "tc-1",
      name: "get_dashboard",
      args: {},
    });
    expect(state.streamingId).toBeNull();
    expect(state.items).toHaveLength(1);
    expect(state.items[0]).toMatchObject({ kind: "tool_call", name: "get_dashboard" });
  });

  it("APPEND_TEXT updates only the matching assistant_text item", () => {
    let state = reducer(INITIAL, { type: "BEGIN_ASSISTANT", id: "a1" });
    state = reducer(state, { type: "APPEND_TEXT", id: "a1", text: "Hello" });
    state = reducer(state, { type: "APPEND_TEXT", id: "a1", text: " world" });
    const item = state.items.find((i) => i.id === "a1");
    expect(item).toBeDefined();
    expect((item as { kind: string; text: string }).text).toBe("Hello world");
  });

  it("CLEAR_ERROR clears error without touching isStreaming", () => {
    const withError: AgentState = { ...INITIAL, isStreaming: true, error: "oops" };
    const state = reducer(withError, { type: "CLEAR_ERROR" });
    expect(state.error).toBeNull();
    expect(state.isStreaming).toBe(true);
  });

  it("BEGIN_ASSISTANT then ERROR: spinner fully cleared", () => {
    let state = reducer(INITIAL, { type: "ADD_USER", id: "u1", text: "hi" });
    state = reducer(state, { type: "BEGIN_ASSISTANT", id: "a1" });
    state = reducer(state, { type: "APPEND_TEXT", id: "a1", text: "part…" });
    // Simulate stream interruption
    state = reducer(state, { type: "ERROR", message: "Stream interrupted." });
    expect(state.isStreaming).toBe(false);
    expect(state.streamingId).toBeNull();
    expect(state.error).toBe("Stream interrupted.");
  });
});
