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
import { useMemo, useState, type ReactNode } from "react";
import { SortableWidgetCard } from "./SortableWidgetCard";
import type { WorkspaceWidget } from "@/lib/agentTypes";
import {
  SECTIONS,
  SECTION_DESCRIPTIONS,
  SECTION_LABELS,
  flattenForReorder,
  groupBySection,
  pickHeroSection,
  splitHeroWidgets,
} from "@/lib/dashboardSections";

type DragState = { widgetsRef: WorkspaceWidget[]; order: string[] };

export function Workspace({
  widgets,
  onDelete,
  onReorder,
  isLoading,
  error,
  onRetry,
  onDismissError,
  presentationMode = false,
  scrollHeader,
}: {
  widgets: WorkspaceWidget[];
  onDelete: (widgetId: string) => void;
  onReorder?: (widgetIds: string[]) => void;
  isLoading: boolean;
  error?: string | null;
  onRetry?: () => void;
  onDismissError?: () => void;
  presentationMode?: boolean;
  scrollHeader?: ReactNode;
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
      <div className="flex h-full items-center justify-center bg-surface">
        <div className="rounded-lg border border-border bg-surface-card px-4 py-3 text-sm text-text-secondary shadow-sm">
          <span className="mr-2 inline-block h-4 w-4 animate-spin rounded-full border-2 border-brand border-t-transparent align-[-2px]" />
          Preparing workspace
        </div>
      </div>
    );
  }

  if (error && ordered.length === 0) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-surface">
        <div className="shrink-0 px-5 pb-2 pt-4">
          <h2 className="text-sm font-semibold uppercase tracking-widest text-text-secondary">
            Dashboard
          </h2>
        </div>
        <div className="flex flex-1 items-center justify-center px-4">
          <div
            data-testid="workspace-error-banner"
            className="max-w-sm rounded-lg border border-red-200 bg-surface-card px-8 py-10 text-center shadow-sm dark:border-red-900/50 dark:bg-surface-elevated"
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

  // Presentation mode: compact report layout — no drag handles, no empty section bodies.
  if (presentationMode && ordered.length > 0) {
    return (
      <div className="flex h-full flex-col overflow-hidden bg-surface">
        <div className="flex shrink-0 items-center justify-between border-b border-border bg-surface-card/95 px-5 py-3 backdrop-blur">
          <div className="flex items-center gap-2.5">
            <span
              data-testid="presentation-mode-badge"
              className="rounded-full border border-warning/30 bg-warning-soft px-2.5 py-0.5 text-xs font-medium text-warning dark:border-amber-400/25 dark:bg-amber-950/40 dark:text-amber-200"
            >
              Presentation
            </span>
            <span className="text-xs text-text-muted">
              {ordered.length} widget{ordered.length !== 1 ? "s" : ""}
            </span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {scrollHeader}
          <div className="px-4 py-4">
            {SECTIONS.map((sectionId) => {
              const sectionWidgets = grouped[sectionId];
              if (sectionWidgets.length === 0) return null;
              const cols =
                sectionWidgets.length === 1
                  ? "grid-cols-1"
                  : sectionWidgets.length === 2
                    ? "grid-cols-2"
                    : "grid-cols-2 xl:grid-cols-3";
              return (
                <div
                  key={sectionId}
                  data-testid={`workspace-section-${sectionId}`}
                  className="mb-4"
                >
                  <p className="mb-2 text-[10px] font-semibold uppercase tracking-widest text-text-muted">
                    {SECTION_LABELS[sectionId]}
                  </p>
                  <div className={`grid gap-3 ${cols}`}>
                    {sectionWidgets.map((widget) => (
                      <SortableWidgetCard
                        key={widget.id}
                        widget={widget}
                        onDelete={onDelete}
                        prominence="standard"
                        readOnly={true}
                      />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-surface">
      <div className="flex shrink-0 items-center justify-between border-b border-border bg-surface-card/95 px-5 py-4 backdrop-blur">
        <div className="min-w-0">
          <p className="text-[10px] font-semibold uppercase tracking-widest text-brand">
            Analytics canvas
          </p>
          <h2 className="mt-0.5 text-lg font-semibold text-text-primary">Dashboard</h2>
          <p className="mt-0.5 text-xs text-text-muted">
            Story-driven business insight, organized for presentation.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {ordered.length >= 2 && !presentationMode && (
            <button
              type="button"
              data-testid="clean-layout-button"
              onClick={handleCleanLayout}
              disabled={justOrganized}
              className={`rounded-lg border px-3 py-1.5 text-xs font-medium transition-all ${
                justOrganized
                  ? "cursor-default border-brand/30 bg-brand/10 text-brand"
                  : "border-border bg-surface-card text-text-secondary shadow-sm hover:-translate-y-0.5 hover:border-brand/30 hover:text-text-primary"
              }`}
            >
              {justOrganized ? "Organized" : "Clean layout"}
            </button>
          )}
          {ordered.length > 0 && (
            <span className="rounded-full border border-border bg-surface px-2.5 py-1 text-xs text-text-muted shadow-sm">
              {ordered.length} widget{ordered.length !== 1 ? "s" : ""}
            </span>
          )}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {scrollHeader}
        <div className="px-5 py-5">
          {error && ordered.length > 0 && (
            <div className="mb-3 rounded-lg border border-red-200 bg-surface-card px-3 py-2 text-xs text-red-700 shadow-sm dark:border-red-900/50 dark:bg-surface-elevated dark:text-red-200">
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
                className="max-w-sm rounded-lg border border-dashed border-border bg-surface-card px-8 py-12 text-center shadow-sm"
              >
                <div className="mx-auto mb-3 h-8 w-8 rounded-lg bg-brand-light" />
                <p className="text-sm font-semibold text-text-primary">No pinned insights yet</p>
                <p className="mt-1 text-xs leading-relaxed text-text-muted">
                  Ask the business copilot a question, then tap{" "}
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
                  const { hero, supporting } = splitHeroWidgets(
                    sectionId,
                    heroSection,
                    sectionWidgets,
                  );
                  return (
                    <div
                      key={sectionId}
                      data-testid={`workspace-section-${sectionId}`}
                      className={`animate-rise-in rounded-lg border px-4 py-5 ${
                        isHeroSection
                          ? "border-border bg-surface-card shadow-sm"
                          : "border-border/80 bg-surface-elevated/90"
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
                        <span className="rounded-full border border-border bg-surface px-2 py-0.5 text-xs text-text-muted">
                          {sectionWidgets.length}
                        </span>
                      </div>
                      <SortableContext
                        items={sectionWidgets.map((w) => w.id)}
                        strategy={rectSortingStrategy}
                      >
                        {hero && (
                          <div
                            data-testid="workspace-hero-lane"
                            className="mb-4 grid grid-cols-2 gap-4 xl:grid-cols-4"
                          >
                            <SortableWidgetCard
                              key={hero.id}
                              widget={hero}
                              onDelete={onDelete}
                              prominence="hero"
                              readOnly={false}
                            />
                          </div>
                        )}
                        {supporting.length > 0 && (
                          <div
                            data-testid={hero ? "workspace-supporting-lane" : undefined}
                            className="grid grid-cols-2 gap-4 xl:grid-cols-3 2xl:grid-cols-4"
                          >
                            {supporting.map((widget) => (
                              <SortableWidgetCard
                                key={widget.id}
                                widget={widget}
                                onDelete={onDelete}
                                prominence="standard"
                                readOnly={false}
                              />
                            ))}
                          </div>
                        )}
                      </SortableContext>
                    </div>
                  );
                })}
              </div>
            </DndContext>
          )}
        </div>
      </div>
    </div>
  );
}
