// Maps internal sandbox/sim place_ids to human-friendly demo names so the UI
// never surfaces raw identifiers like `sim_lager_ale_tlv` or `Business (sim_...)`.
// Backend identifiers and routes are NOT changed; this is render-only.

const PLACE_ID_OVERRIDES: Record<string, string> = {
  sim_lager_ale_tlv: "Craft Lager Bar (Demo)",
  offline_lager_ale: "Craft Lager Bar (Demo)",
  offline_lager_ale_raanana: "Lager & Ale — Ra'anana (Demo)",
  offline_lager_ale_herzliya: "Lager & Ale — Herzliya (Demo)",
  offline_lager_ale_branch4: "Lager & Ale — Petah Tikva (Demo)",
  offline_beer_garden: "Beer Garden (Demo)",
  offline_rami_levy: "Rami Levy — Ariel (Demo)",
  offline_shupersal: "Shupersal Deal — Ariel (Demo)",
  offline_lala_market: "Lala Market (Demo)",
};

const KEYWORD_FALLBACKS: Array<[RegExp, string]> = [
  [/lager|ale/i, "Craft Lager Bar (Demo)"],
  [/beer|brew|tap|pub/i, "Beer Garden (Demo)"],
  [/sushi|wine/i, "Wine & Sushi (Demo)"],
  [/burger|grill/i, "Burger Spot (Demo)"],
  [/coffee|cafe|café/i, "Corner Cafe (Demo)"],
  [/gym|fit/i, "Iron Gym (Demo)"],
  [/market|grocer|levy|shupersal/i, "Neighborhood Market (Demo)"],
];

function titleizeSlug(slug: string): string {
  return slug
    .replace(/^(sim|offline)_/i, "")
    .split(/[_\s-]+/)
    .filter(Boolean)
    .map((part) => part[0]?.toUpperCase() + part.slice(1).toLowerCase())
    .join(" ");
}

function looksLikeRawId(name: string): boolean {
  // Raw or partial sim_*/offline_* identifier surfaced as a name.
  return /\b(sim|offline)[_\s-][a-z0-9]/i.test(name) || /\bsim_/i.test(name);
}

function looksGeneric(name: string): boolean {
  return /^(business|untitled|unknown|place|demo)$/i.test(name.trim());
}

function isSandboxPlaceId(placeId: string | null | undefined): boolean {
  if (!placeId) return false;
  return /^(sim|offline)_/i.test(placeId);
}

/**
 * Render-only friendly name for a business.
 * Falls back to the original name when no mapping or heuristic applies.
 */
export function displayBusinessName(input: {
  place_id?: string | null;
  name?: string | null;
}): string {
  const placeId = (input.place_id ?? "").trim();
  const rawName = (input.name ?? "").trim();

  if (placeId && PLACE_ID_OVERRIDES[placeId]) return PLACE_ID_OVERRIDES[placeId];

  if (isSandboxPlaceId(placeId)) {
    // Strip "— Sim" / "(sim_*)" suffixes from the seeded name.
    const cleaned = rawName
      .replace(/\s*[—-]\s*Sim\s*$/i, "")
      .replace(/\s*\(sim_[^)]*\)\s*$/i, "")
      .trim();

    if (cleaned && !looksLikeRawId(cleaned) && !looksGeneric(cleaned)) {
      return cleaned.endsWith("(Demo)") ? cleaned : `${cleaned} (Demo)`;
    }

    for (const [pattern, label] of KEYWORD_FALLBACKS) {
      if (pattern.test(placeId) || pattern.test(rawName)) return label;
    }

    const slugged = titleizeSlug(placeId);
    return slugged ? `${slugged} (Demo)` : "Demo Business";
  }

  if (rawName && looksLikeRawId(rawName)) {
    for (const [pattern, label] of KEYWORD_FALLBACKS) {
      if (pattern.test(rawName)) return label;
    }
    return "Demo Business";
  }

  return rawName || "Untitled business";
}
