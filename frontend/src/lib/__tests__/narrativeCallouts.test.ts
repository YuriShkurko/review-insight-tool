import { describe, expect, it } from "vitest";
import { createNarrativeCallouts } from "../narrativeCallouts";
import type { Dashboard } from "../types";

function dashboard(overrides: Partial<Dashboard> = {}): Dashboard {
  return {
    place_id: "place-1",
    business_name: "Demo Cafe",
    business_type: "cafe",
    address: "1 Demo St",
    avg_rating: 4.2,
    total_reviews: 42,
    top_complaints: [],
    top_praise: [],
    ai_summary: null,
    action_items: [],
    risk_areas: [],
    recommended_focus: null,
    analysis_created_at: null,
    last_updated_at: null,
    ...overrides,
  };
}

describe("createNarrativeCallouts", () => {
  it("creates data-backed callouts from full dashboard analysis", () => {
    const callouts = createNarrativeCallouts(
      dashboard({
        ai_summary: "Recent reviews improved but service speed still needs attention.",
        top_complaints: [{ label: "Slow service", count: 7 }],
        top_praise: [{ label: "Friendly staff", count: 11 }],
        recommended_focus: "Reduce wait time during evening rush.",
      }),
    );

    expect(callouts.map((c) => c.id)).toEqual([
      "what-changed",
      "main-risk",
      "best-opportunity",
      "next-move",
    ]);
    expect(callouts.find((c) => c.id === "main-risk")?.text).toBe("Slow service (7 mentions)");
    expect(callouts.find((c) => c.id === "best-opportunity")?.text).toBe(
      "Friendly staff (11 mentions)",
    );
  });

  it("prefers explicit risk areas and falls back to action item for next move", () => {
    const callouts = createNarrativeCallouts(
      dashboard({
        top_complaints: [{ label: "Price confusion", count: 3 }],
        risk_areas: ["Weekend staffing gap"],
        action_items: ["Add one more host on Fridays."],
      }),
    );

    expect(callouts.find((c) => c.id === "main-risk")?.text).toBe("Weekend staffing gap");
    expect(callouts.find((c) => c.id === "next-move")?.text).toBe("Add one more host on Fridays.");
    expect(callouts.some((c) => c.id === "what-changed")).toBe(false);
  });

  it("omits callouts when analysis fields are missing", () => {
    expect(createNarrativeCallouts(dashboard())).toEqual([]);
  });
});
