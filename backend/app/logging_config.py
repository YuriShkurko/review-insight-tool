"""Structured logging setup for the backend."""

import logging
import time
from contextlib import contextmanager

LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(name)s | %(message)s"


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(format=LOG_FORMAT, level=level, force=True)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


@contextmanager
def timed_operation(logger: logging.Logger, operation: str, **extra: object):
    """Context manager that logs operation start, duration, and success/failure."""
    start = time.perf_counter()
    context = " ".join(f"{k}={v}" for k, v in extra.items() if v is not None)
    try:
        yield
        duration_ms = round((time.perf_counter() - start) * 1000)
        logger.info("op=%s %s duration_ms=%d success=true", operation, context, duration_ms)
    except Exception as exc:
        duration_ms = round((time.perf_counter() - start) * 1000)
        error_type = type(exc).__name__
        logger.error(
            "op=%s %s duration_ms=%d success=false error=%s",
            operation,
            context,
            duration_ms,
            error_type,
        )
        raise
