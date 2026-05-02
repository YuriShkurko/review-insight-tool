import type { Dashboard } from "./types";

export interface NarrativeCallout {
  id: "what-changed" | "main-risk" | "best-opportunity" | "next-move";
  label: string;
  text: string;
  tone: "neutral" | "risk" | "positive" | "action";
}

function firstText(values: Array<string | null | undefined>): string | null {
  for (const value of values) {
    const trimmed = value?.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function withCount(label: string, count?: number): string {
  return count && count > 0 ? `${label} (${count} mention${count !== 1 ? "s" : ""})` : label;
}

export function createNarrativeCallouts(dashboard: Dashboard): NarrativeCallout[] {
  const callouts: NarrativeCallout[] = [];
  const topIssue = dashboard.top_complaints[0];
  const topPraise = dashboard.top_praise[0];

  const changed = firstText([dashboard.ai_summary]);
  if (changed) {
    callouts.push({
      id: "what-changed",
      label: "What changed",
      text: changed,
      tone: "neutral",
    });
  }

  const risk = firstText([dashboard.risk_areas[0], topIssue?.label]);
  if (risk) {
    callouts.push({
      id: "main-risk",
      label: "Main risk",
      text: topIssue?.label === risk ? withCount(risk, topIssue.count) : risk,
      tone: "risk",
    });
  }

  if (topPraise?.label) {
    callouts.push({
      id: "best-opportunity",
      label: "Best opportunity",
      text: withCount(topPraise.label, topPraise.count),
      tone: "positive",
    });
  }

  const nextMove = firstText([dashboard.recommended_focus, dashboard.action_items[0]]);
  if (nextMove) {
    callouts.push({
      id: "next-move",
      label: "What to do next",
      text: nextMove,
      tone: "action",
    });
  }

  return callouts;
}
