# v3.5.0 — Persistence, agent widget removal, mobile reload stability

Implements scribe spec **RVW-SPC-9** (Persistence + Agent Widget Removal).

## What's New

### Workspace load-error UI (`frontend/src/components/agent/Workspace.tsx`)
- `Workspace` now accepts `error?: string | null` and `onRetry?: () => void`.
- On error with no widgets, renders a red dashed-border state with a Retry
  button — replaces the silent "empty workspace, no feedback" failure mode
  where `LOAD_ERROR` set `state.error` but the UI never read it.
- `frontend/src/app/businesses/[id]/page.tsx` passes `error={state.error}`
  and `onRetry={reload}` to both desktop and mobile Workspace mounts.

### Chat history persistence across refresh (`frontend/src/lib/useAgentChat.ts`)
- New `SEED_HISTORY` reducer action replaces items and clears `isStreaming`.
- `conversationId` is read from `localStorage.conv_${businessId}` via a lazy
  `useState` initializer (SSR-safe in Next.js App Router) and persisted
  after every `done` SSE.
- On mount, hydrates history via the new conversation-detail API; filters
  to user/assistant rows with non-null `content` so tool-call stubs are not
  replayed. 404 is silently treated as a fresh chat (correct for expired
  conversations).

### Conversation detail API (`backend/app/routes/agent.py`, `schemas/agent.py`)
- New `GET /api/businesses/{business_id}/agent/conversations/{conversation_id}`
  returns `ConversationDetail { id, title, messages[], created_at,
  updated_at }`.
- Filters by `conversation_id + business_id + current_user.id`. Returns 404
  for cross-user access.

### Agent-driven widget removal (`backend/app/agent/tools.py`, `executor.py`)
- New `remove_widget` tool. Single required param `widget_id` (UUID
  format). Validates UUID before DB query; returns
  `{removed: false, error: ...}` on invalid format or wrong owner; else
  `{removed: true, widget_id}` after `db.delete + commit`.
- Executor emits a `workspace_event` SSE
  `{action: "widget_removed", widget_id}` after a successful removal.
- `frontend/src/lib/useAgentChat.ts` `dispatchWorkspaceEvent` adds a
  `widget_removed` branch dispatching `WIDGET_REMOVED` to the blackboard.
- System prompt adds a `DASHBOARD REMOVAL` section instructing the agent to
  use the exact UUID from current-turn tool history and never fabricate IDs.

### Mobile workspace reload stabilisation (commit `ea83404`)
- `LOAD_ERROR` reducer preserves existing widgets so a reconciliation
  failure no longer wipes the dashboard.
- `Workspace` shows the failure as a small banner above the existing widget
  grid (not the full-page failed state) when widgets are present.
- `getApiBaseUrl()` rewrites `localhost:8000` to the current page host when
  the page is being viewed on a non-localhost address — makes mobile/LAN
  testing work without env changes (a phone hitting the desktop's LAN IP
  routes API calls to the same LAN IP automatically).
- `backend/app/main.py` adds a private-LAN regex to the CORS middleware so
  RFC1918 ranges (`10.x`, `192.168.x`, `172.16-31.x`) are accepted in dev.
  Production still relies on explicit `CORS_ORIGINS`.

### Tests added

**Backend**
- `tests/unit/test_agent_tools.py` — `TestRemoveWidget` covering happy path
  (mock DB), missing widget, invalid UUID format, wrong owner.
- `tests/integration/test_agent_flow.py` — pin-widget survives reload,
  `GET /agent/conversations/{id}` happy path, cross-user 404,
  `remove_widget` tool emits `workspace_event`, REST DELETE round trip.

**Frontend**
- `src/lib/__tests__/useAgentChat.reducer.test.ts` — `SEED_HISTORY` replaces
  items and clears `isStreaming`; `BEGIN_ASSISTANT` + `ERROR` clears the
  spinner fully.
- `src/lib/__tests__/workspaceBlackboard.test.ts` — `dispatchWorkspaceEvent`
  `widget_removed` dispatch; `WIDGET_REMOVED` for unknown id leaves other
  widgets intact; `LOAD_ERROR` preserves widgets.
- `src/lib/__tests__/api.test.ts` — `getApiBaseUrl` keeps localhost when the
  page is local; uses page host for LAN dev.

## Upgrade Notes

- No database migrations needed.
- `localStorage.conv_${businessId}` is the new chat-restore key. Clearing
  site data resets chats per-business.
- Backend dev defaults already accept private-LAN origins; no
  `CORS_ORIGINS` change needed for local mobile testing.

## Breaking Changes

None.

## Full Changelog

v3.4.0...v3.5.0
