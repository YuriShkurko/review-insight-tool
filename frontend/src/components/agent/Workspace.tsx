import { WidgetRenderer } from "./WidgetRenderer";
import type { WorkspaceWidget } from "@/lib/agentTypes";

export function Workspace({
  widgets,
  onDelete,
  isLoading,
}: {
  widgets: WorkspaceWidget[];
  onDelete: (widgetId: string) => void;
  isLoading: boolean;
}) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <span className="inline-block h-5 w-5 border-2 border-blue-600 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col overflow-hidden">
      <div className="shrink-0 px-4 pt-4 pb-2">
        <h2 className="text-xs font-semibold text-gray-400 uppercase tracking-widest">Workspace</h2>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-4">
        {widgets.length === 0 ? (
          <div className="text-center py-12 text-sm text-gray-400">
            <p>No pinned insights yet.</p>
            <p className="mt-1 text-xs">Ask the AI agent something, then pin the result here.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {widgets.map((widget) => (
              <div
                key={widget.id}
                className="bg-white border border-gray-200 rounded-xl overflow-hidden"
              >
                <div className="px-3 py-2 border-b border-gray-100 flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{widget.title}</p>
                    <p className="text-xs text-gray-400 capitalize">
                      {widget.widget_type.replace(/_/g, " ")}
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={() => onDelete(widget.id)}
                    aria-label="Remove widget"
                    className="shrink-0 text-gray-300 hover:text-red-500 transition-colors text-xl leading-none"
                  >
                    ×
                  </button>
                </div>
                <div className="p-3">
                  <WidgetRenderer widgetType={widget.widget_type} data={widget.data} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
