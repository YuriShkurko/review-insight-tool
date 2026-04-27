/**
 * Tests for LineChart.formatLabel — verifies ISO date strings are parsed as local
 * dates, not UTC midnight, so users in UTC− timezones see the correct day.
 */

import { describe, it, expect } from "vitest";
import { formatLabel } from "../LineChart";

describe("formatLabel", () => {
  it("returns a formatted date string using local date components", () => {
    // Build the expected value using the same local-date approach.
    const expected = new Date(2024, 0, 15).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    expect(formatLabel("2024-01-15")).toBe(expected);
  });

  it("does not produce the UTC-shifted date in negative-offset timezones", () => {
    // new Date("2024-01-15") is UTC midnight; in UTC-5 that would be Jan 14.
    // Our fix constructs a local-midnight date so it must always equal Jan 15 local.
    const result = formatLabel("2024-01-15");
    // Correct: local-date construction (no timezone shift).
    const correct = new Date(2024, 0, 15).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    expect(result).toBe(correct);
    // Ensure we're not accidentally returning an empty string or the raw ISO.
    expect(result.length).toBeGreaterThan(0);
    expect(result).not.toBe("2024-01-15");
  });

  it("passes through strings that are not valid ISO dates", () => {
    expect(formatLabel("not-a-date")).toBe("not-a-date");
    expect(formatLabel("")).toBe("");
  });

  it("handles single-digit month and day without error", () => {
    const result = formatLabel("2024-03-05");
    const expected = new Date(2024, 2, 5).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
    });
    expect(result).toBe(expected);
  });
});
