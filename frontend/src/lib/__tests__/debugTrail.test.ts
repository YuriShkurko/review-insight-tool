/**
 * T1.4 — Tests for debugTrail trace_id capture.
 *
 * Tests cover:
 * - DebugEvent interface has optional trace_id field
 * - trailEvent stores trace_id in the event when provided
 * - trace_id is absent (undefined) when not provided
 * - getTrail() returns events with trace_id intact
 * - sensitive key filtering does NOT strip trace_id
 */

import { describe, it, expect, beforeEach, vi } from "vitest";

// Force the trail enabled by stubbing the env before import
vi.stubEnv("NEXT_PUBLIC_DEBUG_TRAIL", "true");

// Dynamic import so the module sees the stubbed env
const trailModule = await import("../debugTrail");
const { trailEvent, getTrail, clearTrail } = trailModule;

beforeEach(() => {
  clearTrail();
});

describe("DebugEvent trace_id field", () => {
  it("trailEvent stores trace_id when provided in detail", () => {
    trailEvent("api:ok", { trace_id: "abc-123", status: 200 });
    const events = getTrail();
    expect(events).toHaveLength(1);
    expect(events[0].detail?.trace_id).toBe("abc-123");
  });

  it("trace_id is undefined when not provided", () => {
    trailEvent("api:start", { method: "POST", path: "/api/businesses" });
    const events = getTrail();
    expect(events[0].detail?.trace_id).toBeUndefined();
  });

  it("trace_id survives the sanitize pass (not stripped as sensitive)", () => {
    trailEvent("api:ok", { trace_id: "xyz-789", token: "should-be-stripped" });
    const events = getTrail();
    expect(events[0].detail?.trace_id).toBe("xyz-789");
    expect(events[0].detail?.token).toBeUndefined();
  });

  it("multiple events each carry their own trace_id", () => {
    trailEvent("api:start", { trace_id: "t1", method: "POST" });
    trailEvent("api:ok",    { trace_id: "t1", status: 200 });
    trailEvent("api:start", { trace_id: "t2", method: "GET" });
    const events = getTrail();
    const ids = events.map((e) => e.detail?.trace_id);
    expect(ids).toEqual(["t1", "t1", "t2"]);
  });
});

describe("DebugEvent TypeScript interface", () => {
  it("DebugEvent type accepts trace_id in detail without TS error", () => {
    // This is a compile-time check baked into the import; if DebugEvent
    // does not allow trace_id in detail this file will fail to type-check.
    const event: import("../debugTrail").DebugEvent = {
      ts: Date.now(),
      kind: "api:ok",
      route: "/dashboard",
      detail: { trace_id: "compile-check", status: 200 },
    };
    expect(event.detail?.trace_id).toBe("compile-check");
  });
});
