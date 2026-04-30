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
import { useState, useMemo } from "react";
import { SortableWidgetCard } from "./SortableWidgetCard";
import type { WorkspaceWidget } from "@/lib/agentTypes";

// Tracks an in-flight drag reorder. widgetsRef is the widgets array at the time
// the drag ended; when the parent refreshes widgets the reference changes,
// which invalidates the optimistic order without needing a useEffect reset.
type DragState = { widgetsRef: WorkspaceWidget[]; order: string[] };

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

  const ordered = useMemo(() => {
    const sorted = [...widgets].sort((a, b) => a.position - b.position);
    // Only apply the optimistic order if it was set against the same widgets
    // reference — once loadWorkspace() sets a new array, server order wins.
    if (!dragState || dragState.widgetsRef !== widgets) return sorted;
    const map = new Map(sorted.map((w) => [w.id, w]));
    const fromOrder = dragState.order.map((id) => map.get(id)).filter(Boolean) as WorkspaceWidget[];
    const inOrder = new Set(dragState.order);
    const extra = sorted.filter((w) => !inOrder.has(w.id));
    return [...fromOrder, ...extra];
  }, [widgets, dragState]);

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

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-surface">
        <span className="inline-block h-5 w-5 border-2 border-brand border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (error && ordered.length === 0) {
    return (
      <div className="h-full flex flex-col overflow-hidden bg-surface">
        <div className="shrink-0 px-4 pt-4 pb-2">
          <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-widest">
            Dashboard
          </h2>
        </div>
        <div className="flex-1 flex items-center justify-center px-4">
          <div className="text-center border-2 border-dashed border-red-300 rounded-xl px-8 py-10 max-w-sm bg-red-50 dark:bg-red-950/20 dark:border-red-900">
            <p className="text-sm font-medium text-red-700 dark:text-red-300">{error}</p>
            <div className="mt-4 flex items-center justify-center gap-3">
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 transition-colors"
                >
                  Retry
                </button>
              )}
              {onDismissError && (
                <button
                  type="button"
                  onClick={onDismissError}
                  className="inline-flex items-center justify-center rounded-lg border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-100 transition-colors dark:border-red-900 dark:text-red-200 dark:hover:bg-red-950/40"
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
    <div className="h-full flex flex-col overflow-hidden bg-surface">
      <div className="shrink-0 px-4 pt-4 pb-2 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-text-secondary uppercase tracking-widest">
          Dashboard
        </h2>
        {ordered.length > 0 && (
          <span className="text-xs text-text-muted">
            {ordered.length} widget{ordered.length !== 1 ? "s" : ""}
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {error && ordered.length > 0 && (
          <div className="mb-3 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-xs text-red-700 dark:border-red-900 dark:bg-red-950/20 dark:text-red-300">
            <div className="flex items-center justify-between gap-3">
              <span>{error}</span>
              <div className="flex shrink-0 items-center gap-3">
                {onRetry && (
                  <button
                    type="button"
                    onClick={onRetry}
                    className="font-medium text-red-800 hover:text-red-950 dark:text-red-200"
                  >
                    Retry
                  </button>
                )}
                {onDismissError && (
                  <button
                    type="button"
                    onClick={onDismissError}
                    aria-label="Dismiss error"
                    className="font-medium text-red-800 hover:text-red-950 dark:text-red-200"
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
          </div>
        )}
        {ordered.length === 0 ? (
          <div className="h-full flex items-center justify-center">
            <div className="text-center border-2 border-dashed border-border rounded-2xl px-8 py-12 max-w-xs">
              <div className="text-3xl mb-3">✦</div>
              <p className="text-sm font-medium text-text-secondary">No pinned insights yet</p>
              <p className="mt-1 text-xs text-text-muted leading-relaxed">
                Ask the AI a question, then tap{" "}
                <span className="text-brand font-medium">+ Dashboard</span> to pin results here.
              </p>
            </div>
          </div>
        ) : (
          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <SortableContext items={ordered.map((w) => w.id)} strategy={rectSortingStrategy}>
              <div className="grid grid-cols-2 gap-3">
                {ordered.map((widget) => (
                  <SortableWidgetCard key={widget.id} widget={widget} onDelete={onDelete} />
                ))}
              </div>
            </SortableContext>
          </DndContext>
        )}
      </div>
    </div>
  );
}
