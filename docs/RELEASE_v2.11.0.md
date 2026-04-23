# v2.11.0 — OpenTelemetry instrumentation + synthetic monitoring

## What's New

### OpenTelemetry backend instrumentation (`backend/app/observability.py`)
- New `observability.py` module — wires OTEL traces, metrics, and auto-instrumentation
  in a single `init_observability(app, engine)` call at startup.
- Auto-instruments FastAPI (HTTP spans), SQLAlchemy (query spans), and httpx
  (outbound call spans) via the official OTEL instrumentation packages.
- Exports via OTLP/HTTP to any compatible backend (Grafana Cloud, Jaeger, etc.).
  Fully no-op when `OTEL_EXPORTER_OTLP_ENDPOINT` is unset — no changes to local dev.
- Service resource tagged with `service.name`, `service.version` (git SHA), and
  `deployment.environment`.

### Custom business metrics
Eight instruments added across the service layer:

| Metric | Type | Where |
|--------|------|-------|
| `reviews.fetched` | Counter | `review_service.py` — after provider returns |
| `analyses.run` | Counter | `analysis_service.py` — after successful LLM call |
| `llm.latency_ms` | Histogram | `analysis_service.py` — OpenAI round-trip duration |
| `llm.errors` | Counter | `analysis_service.py` — OpenAI call exceptions |
| `llm.parse_failures` | Counter | `analysis_service.py` — invalid JSON responses |
| `comparisons.run` | Counter | `comparison_service.py` — after comparison completes |
| `comparisons.cache_hits` | Counter | `comparison_service.py` — MongoDB cache hit |
| `comparisons.cache_misses` | Counter | `comparison_service.py` — cache miss, LLM called |

### Synthetic monitoring bot (`scripts/synthetic_monitor.py`)
- End-to-end user-flow exerciser: health → register → create business → fetch reviews →
  analyze → dashboard completeness check → add competitor → analyze competitor →
  comparison (cold) → comparison (cached) → cleanup.
- Exits 1 on any failure; sends a Telegram alert when `TELEGRAM_BOT_TOKEN` and
  `TELEGRAM_CHAT_ID` are set.
- Writes a structured JSON results file to `SYNTHETIC_RESULTS_PATH` for CI artifact upload.

### GitHub Actions cron workflow (`.github/workflows/synthetic.yml`)
- Runs the synthetic monitor on a schedule (every 30 minutes) and on `workflow_dispatch`.
- Exposes `workflow_call` so other workflows can invoke it as a reusable job.
- Uploads the JSON results as a CI artifact (7-day retention).

### Post-deploy smoke test (`.github/workflows/cd.yml`)
- New `smoke-test` job added to the CD pipeline — calls `synthetic.yml` automatically
  after every successful ECS deploy.
- Every push to `main` now ends with a full user-flow validation against the live
  deployment.

### Unit tests (`backend/tests/unit/`)
- `test_analysis_service.py` — covers `_format_reviews_for_prompt`, `_call_openai`
  (success, API error, JSON parse failure), `analyze_reviews` (no-reviews guard,
  overwrite behaviour).
- `test_comparison_service.py` — covers snapshot building, prompt formatting,
  cache hit/miss paths, normalization, mock fallback.

## Upgrade Notes

- No database migrations needed.
- To enable observability in production, store two SSM parameters and add them to the
  ECS task definition secrets block (see `docs/OBSERVABILITY_PLAN.md`):
  - `/review-insight/OTEL_EXPORTER_OTLP_ENDPOINT`
  - `/review-insight/OTEL_EXPORTER_OTLP_HEADERS`
- `infrastructure/05-ecs.sh` updated to include both OTEL secrets — safe to re-run.
- To enable Telegram alerts for the synthetic monitor, add two GitHub Actions secrets:
  `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.
- `MONITOR_BASE_URL` GitHub variable must be set to the backend public URL for the
  cron workflow to target the live deployment.

## Breaking Changes

None. All new instrumentation is additive and no-ops without configuration.

## Full Changelog

v2.10.0...v2.11.0
