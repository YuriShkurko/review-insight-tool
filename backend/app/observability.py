"""Production observability via OpenTelemetry → Grafana Cloud.

No-op when OTEL_EXPORTER_OTLP_ENDPOINT is not set (local dev, CI).
"""

import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

logger = logging.getLogger(__name__)

# --- Business metric counters (no-op until init_observability is called) ---

_meter = metrics.get_meter("review-insight")

reviews_fetched = _meter.create_counter(
    "reviews.fetched", description="Total reviews fetched from providers"
)
analyses_run = _meter.create_counter("analyses.run", description="Total analysis runs")
comparisons_run = _meter.create_counter("comparisons.run", description="Total comparison runs")
comparison_cache_hits = _meter.create_counter(
    "comparisons.cache_hits", description="Comparison cache hits (MongoDB)"
)
comparison_cache_misses = _meter.create_counter(
    "comparisons.cache_misses", description="Comparison cache misses"
)
llm_errors = _meter.create_counter("llm.errors", description="LLM call failures")
llm_parse_failures = _meter.create_counter(
    "llm.parse_failures", description="LLM returned invalid JSON"
)
llm_latency = _meter.create_histogram(
    "llm.latency_ms", description="LLM call latency in milliseconds"
)


def init_observability(app, db_engine) -> None:
    """Initialize OTEL if OTEL_EXPORTER_OTLP_ENDPOINT is set. No-op otherwise."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("op=observability status=disabled reason=no_endpoint")
        return

    resource = Resource.create(
        {
            "service.name": "review-insight-backend",
            "service.version": os.environ.get("GIT_SHA", "dev"),
            "deployment.environment": os.environ.get("DEPLOY_ENV", "production"),
        }
    )

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=60_000,
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument FastAPI
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(app)

    # Auto-instrument SQLAlchemy (only if engine is available)
    if db_engine is not None:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor

        SQLAlchemyInstrumentor().instrument(engine=db_engine)

    # Auto-instrument httpx (outbound calls to OpenAI, Outscraper, etc.)
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    HTTPXClientInstrumentor().instrument()

    logger.info("op=observability status=enabled endpoint=%s", endpoint)
