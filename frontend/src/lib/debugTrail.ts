/**
 * Debug-only client-side event ring buffer.
 * Enabled only when NEXT_PUBLIC_DEBUG_TRAIL=true.
 * All public functions are no-ops when the flag is off.
 */

const ENABLED = process.env.NEXT_PUBLIC_DEBUG_TRAIL === "true";
const CAPACITY = 200;

export interface DebugEvent {
  ts: number;
  kind: string;
  route: string;
  detail?: Record<string, unknown>;
}

// Ring buffer state (module-level singleton, client-only)
const _buf: DebugEvent[] = [];
let _head = 0; // next write position
let _size = 0; // number of valid entries

function _currentRoute(): string {
  if (typeof window === "undefined") return "";
  return window.location.pathname;
}

const _SENSITIVE_KEYS = /token|password|authorization|secret/i;

function _sanitize(detail?: Record<string, unknown>): Record<string, unknown> | undefined {
  if (!detail) return undefined;
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(detail)) {
    if (_SENSITIVE_KEYS.test(k)) continue;
    if (typeof v === "string") {
      out[k] = v.length > 200 ? v.slice(0, 200) + "…" : v;
    } else {
      out[k] = v;
    }
  }
  return out;
}

export function isTrailEnabled(): boolean {
  return ENABLED;
}

export function trailEvent(kind: string, detail?: Record<string, unknown>): void {
  if (!ENABLED) return;
  const event: DebugEvent = {
    ts: Date.now(),
    kind,
    route: _currentRoute(),
    detail: _sanitize(detail),
  };
  _buf[_head] = event;
  _head = (_head + 1) % CAPACITY;
  if (_size < CAPACITY) _size++;
}

/** Returns all events in chronological order (oldest first). */
export function getTrail(): DebugEvent[] {
  if (!ENABLED) return [];
  if (_size < CAPACITY) return _buf.slice(0, _size);
  // Buffer is full: oldest is at _head
  return [..._buf.slice(_head), ..._buf.slice(0, _head)];
}

export function clearTrail(): void {
  if (!ENABLED) return;
  _buf.length = 0;
  _head = 0;
  _size = 0;
}

/** Returns a pretty-printed JSON string safe to copy or file-save. */
export function dumpTrail(): string {
  return JSON.stringify(
    {
      generated_at: new Date().toISOString(),
      event_count: _size,
      events: getTrail(),
    },
    null,
    2,
  );
}
