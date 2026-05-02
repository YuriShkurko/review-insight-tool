"use client";

import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  rectSortingStrategy,
  arrayMove,
} from "@dnd-kit/sortable";
import { useMemo, useState } from "react";
import { SortableWidgetCard } from "./SortableWidgetCard";
import type { WorkspaceWidget } from "@/lib/agentTypes";
import {
  SECTIONS,
  SECTION_DESCRIPTIONS,
  SECTION_LABELS,
  flattenForReorder,
  groupBySection,
  type SectionId,
} from "@/lib/dashboardSections";

type DragState = { widgetsRef: WorkspaceWidget[]; order: string[] };

function pickHeroSection(grouped: Record<SectionId, WorkspaceWidget[]>): SectionId | null {
  if (grouped.trends.length > 0) return "trends";
  if (grouped.overview.length > 0) return "overview";
  if (grouped.issues.length > 0) return "issues";
  return null;
}

export function Workspace({
  widgets,
  onDelete,
  onReorder,
  isLoading,
  error,
  onRetry,
  onDismissError,
}: {
  widgets: WorkspaceWidget[];
  onDelete: (widgetId: string) => void;
  onReorder?: (widgetIds: string[]) => void;
  isLoading: boolean;
  error?: string | null;
  onRetry?: () => void;
  onDismissError?: () => void;
}) {
  const [dragState, setDragState] = useState<DragState | null>(null);
  const [justOrganized, setJustOrganized] = useState(false);

  const ordered = useMemo(() => {
    const sorted = [...widgets].sort((a, b) => a.position - b.position);
    if (!dragState || dragState.widgetsRef !== widgets) return sorted;
    const map = new Map(sorted.map((w) => [w.id, w]));
    const fromOrder = dragState.order.map((id) => map.get(id)).filter(Boolean) as WorkspaceWidget[];
    const inOrder = new Set(dragState.order);
    const extra = sorted.filter((w) => !inOrder.has(w.id));
    return [...fromOrder, ...extra];
  }, [widgets, dragState]);

  const grouped = useMemo(() => groupBySection(ordered), [ordered]);
  const heroSection = useMemo(() => pickHeroSection(grouped), [grouped]);

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event;
    if (!over || active.id === over.id) return;
    const currentIds = ordered.map((w) => w.id);
    const oldIndex = currentIds.indexOf(active.id as string);
    const newIndex = currentIds.indexOf(over.id as string);
    const newIds = arrayMove(currentIds, oldIndex, newIndex);
    setDragState({ widgetsRef: widgets, order: newIds });
    onReorder?.(newIds);
  }

  function handleCleanLayout() {
    if (ordered.length < 2) return;
    const cleanIds = flattenForReorder(grouped);
    setDragState({ widgetsRef: widgets, order: cleanIds });
    onReorder?.(cleanIds);
    setJustOrganized(true);
    setTimeout(() => setJustOrganized(false), 1500);
  }

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center bg-[#f6f7fb]">
        <div className="rounded-lg border border-border-subtle bg-white px-4 py-3 text-sm text-text-secondary shadow-sm">
          <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-brand border-t-transparent align-[-2px]" />
          Preparing workspace
        </div>
      </div>
    );
  }

  if (error && ordered.length === 0) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-[#f6f7fb]">
        <div className="shrink-0 px-5 pb-2 pt-4">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-text-secondary">
            Dashboard
          </h2>
        </div>
        <div className="flex flex-1 items-center justify-center px-4">
          <div
            data-testid="workspace-error-banner"
            className="max-w-sm rounded-lg border border-red-200 bg-white px-8 py-10 text-center shadow-sm"
          >
            <p className="text-sm font-medium text-red-700">{error}</p>
            <div className="mt-4 flex items-center justify-center gap-3">
              {onRetry && (
                <button
                  type="button"
                  data-testid="retry-workspace-button"
                  onClick={onRetry}
                  className="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-700"
                >
                  Retry
                </button>
              )}
              {onDismissError && (
                <button
                  type="button"
                  onClick={onDismissError}
                  className="inline-flex items-center justify-center rounded-lg border border-red-200 px-4 py-2 text-sm font-medium text-red-700 transition-colors hover:bg-red-50"
                >
                  Dismiss
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-[#f6f7fb]">
      <div className="flex shrink-0 items-center justify-between border-b border-slate-200/80 bg-white/85 px-5 py-4 backdrop-blur">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-brand">
            Analytics canvas
          </p>
          <h2 className="mt-0.5 text-lg font-semibold text-text-primary">Dashboard</h2>
          <p className="mt-0.5 text-xs text-text-muted">
            Story-driven review intelligence, organized for presentation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {ordered.length >= 2 && (
            <button
              type="button"
              data-testid="clean-layout-button"
              onClick={handleCleanLayout}
              disabled={justOrganized}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                justOrganized
                  ? "cursor-default border-brand/30 bg-brand/10 text-brand"
                  : "border-slate-200 bg-white text-text-secondary shadow-sm hover:-translate-y-0.5 hover:border-brand/30 hover:text-text-primary"
              }`}
            >
              {justOrganized ? "Organized" : "Clean layout"}
            </button>
          )}
          {ordered.length > 0 && (
            <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-text-muted shadow-sm">
              {ordered.length} widget{ordered.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        {error && ordered.length > 0 && (
          <div className="mb-3 rounded-lg border border-red-200 bg-white px-3 py-2 text-xs text-red-700 shadow-sm">
            <div className="flex items-center justify-between gap-3">
              <span>{error}</span>
              <div className="flex shrink-0 items-center gap-3">
                {onRetry && (
                  <button
                    type="button"
                    onClick={onRetry}
                    className="font-medium text-red-800 hover:text-red-950"
                  >
                    Retry
                  </button>
                )}
                {onDismissError && (
                  <button
                    type="button"
                    onClick={onDismissError}
                    aria-label="Dismiss error"
                    className="font-medium text-red-800 hover:text-red-950"
                  >
                    x
                  </button>
                )}
              </div>
            </div>
          </div>
        )}

        {ordered.length === 0 ? (
          <div className="flex h-full items-center justify-center">
            <div
              data-testid="workspace-empty-state"
              className="max-w-sm rounded-lg border border-dashed border-slate-300 bg-white px-8 py-12 text-center shadow-sm"
            >
              <div className="mx-auto mb-3 h-8 w-8 rounded-lg bg-brand-light" />
              <p className="text-sm font-semibold text-text-primary">No pinned insights yet</p>
              <p className="mt-1 text-xs leading-relaxed text-text-muted">
                Ask the AI a question, then tap{" "}
                <span className="font-medium text-brand">+ Dashboard</span> to pin results here.
              </p>
            </div>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <div className="space-y-5">
              {SECTIONS.map((sectionId) => {
                const sectionWidgets = grouped[sectionId];
                if (sectionWidgets.length === 0) return null;
                const isHeroSection = sectionId === heroSection;
                return (
                  <div
                    key={sectionId}
                    data-testid={`workspace-section-${sectionId}`}
                    className={`animate-rise-in rounded-lg border px-4 py-5 ${
                      isHeroSection
                        ? "border-slate-200 bg-white shadow-sm"
                        : "border-slate-200/80 bg-white/70"
                    }`}
                  >
                    <div className="mb-4 flex items-start justify-between gap-3">
                      <div>
                        <p className="text-[10px] font-semibold uppercase tracking-widest text-brand">
                          {isHeroSection ? "Hero insight" : SECTION_LABELS[sectionId]}
                        </p>
                        <h3 className="mt-1 text-base font-semibold text-text-primary">
                          {SECTION_LABELS[sectionId]}
                        </h3>
                        <p className="mt-0.5 text-xs text-text-muted">
                          {SECTION_DESCRIPTIONS[sectionId]}
                        </p>
                      </div>
                      <span className="rounded-full border border-slate-200 bg-white px-2 py-0.5 text-xs text-text-muted">
                        {sectionWidgets.length}
                      </span>
                    </div>
                    <SortableContext
                      items={sectionWidgets.map((w) => w.id)}
                      strategy={rectSortingStrategy}
                    >
                      <div
                        className={`grid grid-cols-2 gap-4 ${
                          isHeroSection ? "xl:grid-cols-4" : "xl:grid-cols-3 2xl:grid-cols-4"
                        }`}
                      >
                        {sectionWidgets.map((widget, index) => (
                          <SortableWidgetCard
                            key={widget.id}
                            widget={widget}
                            onDelete={onDelete}
                            prominence={isHeroSection && index === 0 ? "hero" : "standard"}
                          />
                        ))}
                      </div>
                    </SortableContext>
                  </div>
                );
              })}
            </div>
          </DndContext>
        )}
      </div>
    </div>
  );
}
