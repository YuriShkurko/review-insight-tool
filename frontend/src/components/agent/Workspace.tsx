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

export function Workspace({
  widgets,
  onDelete,
  onReorder,
  isLoading,
}: {
  widgets: WorkspaceWidget[];
  onDelete: (widgetId: string) => void;
  onReorder?: (widgetIds: string[]) => void;
  isLoading: boolean;
}) {
  // dragIdOrder is non-null only during/after a drag, for optimistic reordering
  const [dragIdOrder, setDragIdOrder] = useState<string[] | null>(null);

  const ordered = useMemo(() => {
    const sorted = [...widgets].sort((a, b) => a.position - b.position);
    if (!dragIdOrder) return sorted;
    const map = new Map(sorted.map((w) => [w.id, w]));
    const fromOrder = dragIdOrder.map((id) => map.get(id)).filter(Boolean) as WorkspaceWidget[];
    const inOrder = new Set(dragIdOrder);
    const extra = sorted.filter((w) => !inOrder.has(w.id));
    return [...fromOrder, ...extra];
  }, [widgets, dragIdOrder]);

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
    setDragIdOrder(newIds);
    onReorder?.(newIds);
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full bg-surface">
        <span className="inline-block h-5 w-5 border-2 border-brand border-t-transparent rounded-full animate-spin" />
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
