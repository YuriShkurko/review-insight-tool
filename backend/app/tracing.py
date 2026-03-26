"""E2E request tracing — ring buffer, middleware, and span helpers.

Gated by the DEBUG_TRACE environment variable (must equal "true" to activate).
When disabled every public function/class is a no-op and adds zero overhead.

Usage
-----
# In main.py (already wired via create_app):
    if settings.DEBUG_TRACE:
        app.add_middleware(TraceMiddleware)

# In a route or service:
    with trace_span(trace_context, get_current_trace_id(), "db_query"):
        rows = db.query(Review).all()

# From the debug MCP tools:
    trace_context.get_trace(trace_id)
    trace_context.list_recent(limit=20)

Tuning env vars (all optional):
    DEBUG_TRACE_MAX_TRACES      int   default 500
    DEBUG_TRACE_MAX_SPANS       int   default 50
    DEBUG_TRACE_SAMPLE_RATE     float default 1.0  (0.0-1.0, hash-deterministic)
    DEBUG_TRACE_TTL_HOURS       int   default 24   (set to 0 to disable TTL)
"""

import hashlib
import os
import threading
import time
import uuid
from collections import deque
from collections.abc import Generator
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path
from typing import Any


# Load .env so DEBUG_TRACE and tuning vars are visible via os.environ when this
# module is imported (pydantic-settings populates Settings but not os.environ).
def _load_dotenv_once() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return
    with env_path.open() as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

_load_dotenv_once()

from starlette.middleware.base import BaseHTTPMiddleware  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import Response  # noqa: E402

# ---------------------------------------------------------------------------
# Contextvar — current trace ID for the in-flight request
# ---------------------------------------------------------------------------

_current_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)


def get_current_trace_id() -> str | None:
    """Return the trace ID for the current request context, or None."""
    return _current_trace_id.get()


# ---------------------------------------------------------------------------
# Sampling helper — hash-deterministic so same trace_id always in/out
# ---------------------------------------------------------------------------

def _should_sample(trace_id: str, rate: float) -> bool:
    """Return True if this trace_id should be recorded at *rate* (0.0-1.0).

    Uses the first 8 hex digits of SHA-256(trace_id) as a uniform [0, 1)
    value so the decision is consistent across processes and restarts.
    """
    if rate >= 1.0:
        return True
    if rate <= 0.0:
        return False
    digest = hashlib.sha256(trace_id.encode()).hexdigest()
    value = int(digest[:8], 16) / 0xFFFFFFFF  # maps to [0, 1)
    return value < rate


# ---------------------------------------------------------------------------
# TraceContext — thread-safe in-memory ring buffer
# ---------------------------------------------------------------------------

class TraceContext:
    """In-memory ring buffer of request traces and their spans.

    Parameters
    ----------
    max_traces:
        Maximum number of traces retained.  Oldest is evicted when full.
    max_spans_per_trace:
        Maximum spans stored per trace.  Oldest span is evicted when full.
    enabled:
        When False every method is a no-op.
    sample_rate:
        Fraction of traces to store (0.0-1.0).  Sampling is hash-deterministic:
        the same trace_id always produces the same sampling decision.
    ttl_hours:
        Traces older than this many hours are removed by cleanup().
        None disables TTL.
    """

    def __init__(
        self,
        max_traces: int = 500,
        max_spans_per_trace: int = 50,
        enabled: bool = True,
        sample_rate: float = 1.0,
        ttl_hours: int | None = 24,
    ) -> None:
        self._enabled = enabled
        self._max_traces = max_traces
        self._max_spans = max_spans_per_trace
        self._sample_rate = sample_rate
        self._ttl_hours = ttl_hours
        # deque gives O(1) append + O(1) popleft (eviction)
        self._ring: deque[dict[str, Any]] = deque()
        self._index: dict[str, dict[str, Any]] = {}  # trace_id -> trace dict
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Write API
    # ------------------------------------------------------------------

    def add_trace(self, trace_id: str, *, endpoint: str) -> None:
        if not self._enabled:
            return
        if not _should_sample(trace_id, self._sample_rate):
            return
        trace: dict[str, Any] = {
            "trace_id": trace_id,
            "endpoint": endpoint,
            "started_at": time.time(),
            "spans": deque(),  # internal deque; exposed as list via get_trace
        }
        with self._lock:
            if len(self._ring) >= self._max_traces:
                evicted = self._ring.popleft()
                self._index.pop(evicted["trace_id"], None)
            self._ring.append(trace)
            self._index[trace_id] = trace

    def add_span(
        self,
        trace_id: str,
        *,
        name: str,
        duration_ms: float,
        success: bool,
        metadata: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        if not self._enabled:
            return
        span: dict[str, Any] = {
            "name": name,
            "started_at": time.time(),
            "duration_ms": duration_ms,
            "success": success,
            "metadata": metadata or {},
        }
        if error is not None:
            span["error"] = error
        with self._lock:
            trace = self._index.get(trace_id)
            if trace is None:
                return  # unsampled or evicted — no-op
            spans: deque = trace["spans"]
            if len(spans) >= self._max_spans:
                spans.popleft()
            spans.append(span)

    # ------------------------------------------------------------------
    # Read API
    # ------------------------------------------------------------------

    def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        if not self._enabled:
            return None
        with self._lock:
            trace = self._index.get(trace_id)
            if trace is None:
                return None
            return {**trace, "spans": list(trace["spans"])}

    def list_recent(self, limit: int | None = 20) -> list[dict[str, Any]]:
        """Return traces newest-first, capped at *limit* (None = all)."""
        if not self._enabled:
            return []
        with self._lock:
            items = list(self._ring)
        items.reverse()  # newest first
        if limit is not None:
            items = items[:limit]
        return [{**t, "spans": list(t["spans"])} for t in items]

    # ------------------------------------------------------------------
    # TTL cleanup
    # ------------------------------------------------------------------

    def cleanup(self) -> int:
        """Evict traces older than ttl_hours.  Returns eviction count.

        This is safe to call from a background thread.  If ttl_hours is None
        this is a no-op.
        """
        if not self._enabled or self._ttl_hours is None:
            return 0
        cutoff = time.time() - self._ttl_hours * 3600
        evicted = 0
        with self._lock:
            # Collect IDs to remove; can't mutate ring while iterating
            stale = [t["trace_id"] for t in self._ring if t["started_at"] < cutoff]
            for tid in stale:
                self._index.pop(tid, None)
            # Rebuild ring without stale entries (preserves order)
            self._ring = deque(t for t in self._ring if t["trace_id"] not in set(stale))
            evicted = len(stale)
        return evicted


# ---------------------------------------------------------------------------
# Global singleton — built from env vars; tests use their own instances
# ---------------------------------------------------------------------------

def _build_context() -> TraceContext:
    enabled = os.environ.get("DEBUG_TRACE", "").lower() == "true"
    max_traces = int(os.environ.get("DEBUG_TRACE_MAX_TRACES", "500"))
    max_spans = int(os.environ.get("DEBUG_TRACE_MAX_SPANS", "50"))
    sample_rate = float(os.environ.get("DEBUG_TRACE_SAMPLE_RATE", "1.0"))
    ttl_raw = os.environ.get("DEBUG_TRACE_TTL_HOURS", "24")
    ttl_hours: int | None = int(ttl_raw) if ttl_raw and int(ttl_raw) > 0 else None
    return TraceContext(
        max_traces=max_traces,
        max_spans_per_trace=max_spans,
        enabled=enabled,
        sample_rate=sample_rate,
        ttl_hours=ttl_hours,
    )


# Module-level singleton; tests instantiate their own TraceContext.
trace_context = _build_context()


# ---------------------------------------------------------------------------
# TraceMiddleware — injects / propagates X-Trace-Id
# ---------------------------------------------------------------------------

class TraceMiddleware(BaseHTTPMiddleware):
    """Starlette middleware that:

    1. Reads X-Trace-Id from the incoming request (if present) or generates one.
    2. Stores the trace ID in a contextvar for the duration of the request.
    3. Registers the trace in the global trace_context ring buffer.
    4. Appends X-Trace-Id to the response headers.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())
        token = _current_trace_id.set(trace_id)

        trace_context.add_trace(trace_id, endpoint=str(request.url.path))

        try:
            response: Response = await call_next(request)
            response.headers["x-trace-id"] = trace_id
            return response
        except Exception:
            from starlette.responses import PlainTextResponse
            response = PlainTextResponse("Internal Server Error", status_code=500)
            response.headers["x-trace-id"] = trace_id
            return response
        finally:
            _current_trace_id.reset(token)


# ---------------------------------------------------------------------------
# trace_span — context manager that records a single span
# ---------------------------------------------------------------------------

@contextmanager
def trace_span(
    ctx: TraceContext,
    trace_id: str | None,
    name: str,
    *,
    metadata: dict[str, Any] | None = None,
) -> Generator[None, None, None]:
    """Record a named span inside *trace_id* on *ctx*.

    Measures wall-clock duration and marks success/failure automatically.
    Exceptions are always re-raised.

    Usage::

        with trace_span(trace_context, get_current_trace_id(), "db_query"):
            rows = db.query(Review).all()
    """
    start = time.perf_counter()
    exc_type_name: str | None = None
    try:
        yield
    except Exception as exc:
        exc_type_name = type(exc).__name__
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000
        if trace_id is not None:
            ctx.add_span(
                trace_id,
                name=name,
                duration_ms=round(duration_ms, 3),
                success=exc_type_name is None,
                metadata=metadata,
                error=exc_type_name,
            )
