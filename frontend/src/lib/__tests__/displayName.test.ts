import { describe, it, expect } from "vitest";
import { displayBusinessName } from "../displayName";

describe("displayBusinessName", () => {
  it("uses the place_id override map for known demos", () => {
    expect(
      displayBusinessName({ place_id: "sim_lager_ale_tlv", name: "Lager & Ale (Rothschild) — Sim" }),
    ).toBe("Craft Lager Bar (Demo)");
    expect(displayBusinessName({ place_id: "offline_beer_garden", name: "Beer Garden" })).toBe(
      "Beer Garden (Demo)",
    );
  });

  it("strips '— Sim' suffix on sandbox names without an override", () => {
    expect(
      displayBusinessName({
        place_id: "sim_unknown_place_42",
        name: "Some Bar — Sim",
      }),
    ).toBe("Some Bar (Demo)");
  });

  it("falls back to a keyword label when only a raw sim id is available", () => {
    expect(
      displayBusinessName({ place_id: "sim_beer_gar_xyz", name: "Business (sim_beer_gar_xyz)" }),
    ).toBe("Beer Garden (Demo)");
  });

  it("titleizes an unknown sandbox place_id as a last resort", () => {
    expect(
      displayBusinessName({ place_id: "sim_some_random_thing", name: "" }),
    ).toBe("Some Random Thing (Demo)");
  });

  it("passes real-world names through unchanged", () => {
    expect(displayBusinessName({ place_id: "ChIJ_real_google_id", name: "Real Pizza Place" })).toBe(
      "Real Pizza Place",
    );
  });

  it("collapses raw-id-looking names even without a sandbox place_id", () => {
    expect(displayBusinessName({ place_id: "", name: "Business (sim_burger_99)" })).toBe(
      "Burger Spot (Demo)",
    );
  });

  it("returns a sensible fallback when name is missing", () => {
    expect(displayBusinessName({ place_id: "ChIJ_real", name: "" })).toBe("Untitled business");
  });
});
