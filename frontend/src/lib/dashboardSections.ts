import type { WorkspaceWidget } from "./agentTypes";

export const SECTIONS = ["overview", "trends", "issues", "evidence", "actions"] as const;

export type SectionId = (typeof SECTIONS)[number];

export const SECTION_LABELS: Record<SectionId, string> = {
  overview: "Overview",
  trends: "Trends",
  issues: "Issues",
  evidence: "Evidence",
  actions: "Actions",
};

export const SECTION_DESCRIPTIONS: Record<SectionId, string> = {
  overview: "Current state and executive context.",
  trends: "How review volume and rating quality are moving.",
  issues: "Friction themes that need attention.",
  evidence: "Customer voice behind the signal.",
  actions: "Recommended next moves.",
};

export function pickHeroSection(grouped: Record<SectionId, WorkspaceWidget[]>): SectionId | null {
  if (grouped.trends.length > 0) return "trends";
  if (grouped.overview.length > 0) return "overview";
  if (grouped.issues.length > 0) return "issues";
  return null;
}

export function classifyWidget(w: WorkspaceWidget): SectionId {
  const { widget_type } = w;
  const title = w.title.toLowerCase();
  const data = w.data as Record<string, unknown>;

  if (widget_type === "metric_card" || widget_type === "trend_indicator") return "overview";

  if (widget_type === "summary_card") {
    if (data.action_items || data.recommended_focus) return "actions";
    return "overview";
  }

  if (
    [
      "line_chart",
      "bar_chart",
      "horizontal_bar_chart",
      "comparison_chart",
      "comparison_card",
    ].includes(widget_type)
  )
    return "trends";

  if (widget_type === "pie_chart" || widget_type === "donut_chart") return "issues";

  if (widget_type === "insight_list") {
    if (/action|recommend/.test(title)) return "actions";
    return "issues";
  }

  if (widget_type === "review_list") return "evidence";

  return "overview";
}

export function groupBySection(widgets: WorkspaceWidget[]): Record<SectionId, WorkspaceWidget[]> {
  const result: Record<SectionId, WorkspaceWidget[]> = {
    overview: [],
    trends: [],
    issues: [],
    evidence: [],
    actions: [],
  };
  for (const w of widgets) {
    result[classifyWidget(w)].push(w);
  }
  return result;
}

export function flattenForReorder(grouped: Record<SectionId, WorkspaceWidget[]>): string[] {
  return SECTIONS.flatMap((s) => grouped[s].map((w) => w.id));
}

export function splitHeroWidgets(
  sectionId: SectionId,
  heroSection: SectionId | null,
  widgets: WorkspaceWidget[],
): { hero: WorkspaceWidget | null; supporting: WorkspaceWidget[] } {
  if (sectionId !== heroSection || widgets.length === 0) {
    return { hero: null, supporting: widgets };
  }
  const [hero, ...supporting] = widgets;
  return { hero, supporting };
}
