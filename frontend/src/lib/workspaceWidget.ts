import type { WorkspaceWidget } from "./agentTypes";

const EMPTY_WIDGET: WorkspaceWidget = {
  id: "",
  widget_type: "summary_card",
  title: "Untitled widget",
  data: {},
  position: 0,
  created_at: "",
};

export function normalizeWorkspaceWidget(raw: unknown): WorkspaceWidget {
  const value = (raw ?? {}) as Record<string, unknown>;
  const data = value.data && typeof value.data === "object" ? value.data : {};
  return {
    ...EMPTY_WIDGET,
    id: String(value.id ?? EMPTY_WIDGET.id),
    widget_type: String(value.widget_type ?? value.widgetType ?? EMPTY_WIDGET.widget_type),
    title: String(value.title ?? EMPTY_WIDGET.title),
    data: data as Record<string, unknown>,
    position: typeof value.position === "number" ? value.position : Number(value.position ?? 0),
    created_at: String(value.created_at ?? value.createdAt ?? EMPTY_WIDGET.created_at),
  };
}

export function normalizeWorkspaceWidgets(raw: unknown): WorkspaceWidget[] {
  if (!Array.isArray(raw)) return [];
  return raw.map(normalizeWorkspaceWidget).filter((widget) => widget.id);
}
