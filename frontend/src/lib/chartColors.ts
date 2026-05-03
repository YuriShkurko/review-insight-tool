export const CHART_COLORS = [
  "#7c3aed",
  "#0891b2",
  "#0d9488",
  "#d97706",
  "#e11d48",
  "#2563eb",
] as const;

export function chartColor(index: number): string {
  return CHART_COLORS[index % CHART_COLORS.length];
}
