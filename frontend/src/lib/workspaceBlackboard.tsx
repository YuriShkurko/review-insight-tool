"use client";

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
  type Dispatch,
} from "react";
import { apiFetch, ApiError } from "./api";
import type { WorkspaceWidget } from "./agentTypes";
import { normalizeWorkspaceWidget, normalizeWorkspaceWidgets } from "./workspaceWidget";

// ---------------------------------------------------------------------------
// Actions
// ---------------------------------------------------------------------------

export type WorkspaceAction =
  | { type: "INIT_LOAD" }
  | { type: "LOADED"; widgets: WorkspaceWidget[] }
  | { type: "LOAD_ERROR"; error: string }
  | { type: "WIDGET_ADDED"; widget: WorkspaceWidget }
  | { type: "WIDGET_REMOVED"; widgetId: string }
  | { type: "WIDGET_REORDERED"; widgetIds: string[] };

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------

export interface WorkspaceState {
  widgets: WorkspaceWidget[];
  isLoading: boolean;
  error: string | null;
}

const INITIAL_STATE: WorkspaceState = {
  widgets: [],
  isLoading: true,
  error: null,
};

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case "INIT_LOAD":
      return { ...state, isLoading: state.widgets.length === 0, error: null };

    case "LOADED":
      return { widgets: normalizeWorkspaceWidgets(action.widgets), isLoading: false, error: null };

    case "LOAD_ERROR":
      return { ...state, isLoading: false, error: action.error };

    case "WIDGET_ADDED": {
      const widget = normalizeWorkspaceWidget(action.widget);
      const exists = state.widgets.some((w) => w.id === widget.id);
      if (exists) return state;
      return { ...state, isLoading: false, error: null, widgets: [...state.widgets, widget] };
    }

    case "WIDGET_REMOVED":
      return { ...state, widgets: state.widgets.filter((w) => w.id !== action.widgetId) };

    case "WIDGET_REORDERED": {
      const byId = new Map(state.widgets.map((w) => [w.id, w]));
      const reordered = action.widgetIds
        .map((id) => byId.get(id))
        .filter(Boolean) as WorkspaceWidget[];
      const remaining = state.widgets.filter((w) => !action.widgetIds.includes(w.id));
      const all = [...reordered, ...remaining];
      // Update position fields so sort-by-position in Workspace reflects the new order.
      return { ...state, widgets: all.map((w, i) => ({ ...w, position: i })) };
    }

    default:
      return state;
  }
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

interface WorkspaceContextValue {
  state: WorkspaceState;
  dispatch: Dispatch<WorkspaceAction>;
  reload: () => Promise<void>;
}

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null);

// ---------------------------------------------------------------------------
// Provider
// ---------------------------------------------------------------------------

export function WorkspaceBlackboardProvider({
  businessId,
  children,
}: {
  businessId: string;
  children: ReactNode;
}) {
  const [state, dispatch] = useReducer(workspaceReducer, INITIAL_STATE);
  const activeIdRef = useRef(businessId);

  useEffect(() => {
    activeIdRef.current = businessId;
  }, [businessId]);

  const reload = useCallback(async () => {
    const id = activeIdRef.current;
    dispatch({ type: "INIT_LOAD" });
    try {
      const widgets = await apiFetch<WorkspaceWidget[]>(`/businesses/${id}/agent/workspace`);
      if (activeIdRef.current !== id) return;
      dispatch({ type: "LOADED", widgets });
    } catch (err) {
      if (activeIdRef.current !== id) return;
      const detail = err instanceof ApiError ? err.detail : "Failed to load workspace.";
      dispatch({
        type: "LOAD_ERROR",
        error: detail,
      });
    }
  }, []);

  useEffect(() => {
    reload();
  }, [businessId, reload]);

  return (
    <WorkspaceContext.Provider value={{ state, dispatch, reload }}>
      {children}
    </WorkspaceContext.Provider>
  );
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

export function useWorkspace() {
  const ctx = useContext(WorkspaceContext);
  if (!ctx) throw new Error("useWorkspace must be used within WorkspaceBlackboardProvider");
  return ctx;
}
