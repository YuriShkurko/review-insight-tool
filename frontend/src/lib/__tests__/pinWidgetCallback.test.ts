import { describe, it, expect } from "vitest";
import { shouldTriggerWidgetPinned } from "../useAgentChat";

describe("shouldTriggerWidgetPinned", () => {
  it("returns true for pin_widget with pinned=true", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", { pinned: true })).toBe(true);
  });

  it("returns false for pin_widget with pinned=false", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", { pinned: false })).toBe(false);
  });

  it("returns false for pin_widget with no pinned field", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", {})).toBe(false);
  });

  it("returns false for a different tool even if pinned=true", () => {
    expect(shouldTriggerWidgetPinned("get_dashboard", { pinned: true })).toBe(false);
  });

  it("returns false for pin_widget with pinned=1 (truthy but not boolean true)", () => {
    expect(shouldTriggerWidgetPinned("pin_widget", { pinned: 1 })).toBe(false);
  });
});
