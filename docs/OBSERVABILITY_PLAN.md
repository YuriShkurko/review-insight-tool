# Observability System Plan

> Concrete plan for production observability on Review Insight Tool.
> Goal: run for 5-7 days with synthetic traffic, find real bugs, get phone alerts.
> Budget: $0-5 total.

## Architecture Overview

```
                                  Grafana Cloud (free tier)
                                  ┌─────────────────────────┐
                                  │  Mimir (metrics)        │
  Synthetic Bot ──────────────┐   │  Loki  (logs)           │◄── Alerts ──► Telegram Bot
  (GitHub Actions cron)       │   │  Tempo (traces)         │              (phone push)
                              │   │  Dashboards             │
                              ▼   └──────────▲──────────────┘
                         ┌────────────┐      │
                         │  FastAPI   │      │ OTLP/HTTP
                         │  + OTEL    │──────┘
                         │  (ECS)     │
                         └────┬───────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
               PostgreSQL          MongoDB Atlas
```

## Why This Stack

| Choice | Reason |
|--------|--------|
| **OpenTelemetry** | Industry standard, auto-instruments FastAPI/SQLAlchemy/httpx. Replaces your custom `tracing.py` ring buffer with production-grade traces. Impressive on CV. |
| **Grafana Cloud free tier** | 50GB logs, 10K metric series, 50GB traces/month — more than enough for a week. Zero cost. Real tool used at scale companies. |
| **Telegram bot** | Free, instant phone push, 5 lines of Python. No app to install beyond Telegram. |
| **GitHub Actions cron** | Free synthetic monitoring. No infrastructure to maintain. Runs on a schedule, exercises the full user flow. |

## Phase 1: Instrument the Backend (Day 1)

### 1.1 Add OpenTelemetry dependencies

```
# Add to requirements.txt
opentelemetry-api>=1.25.0
opentelemetry-sdk>=1.25.0
opentelemetry-exporter-otlp-proto-http>=1.25.0
opentelemetry-instrumentation-fastapi>=0.46b0
opentelemetry-instrumentation-sqlalchemy>=0.46b0
opentelemetry-instrumentation-httpx>=0.46b0
opentelemetry-instrumentation-logging>=0.46b0
```

### 1.2 Create `backend/app/observability.py`

Single module that wires everything up. Called once at startup.

```python
"""Production observability via OpenTelemetry → Grafana Cloud."""

import logging
import os

from opentelemetry import trace, metrics
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

logger = logging.getLogger(__name__)

def init_observability(app, db_engine):
    """Initialize OTEL if OTEL_EXPORTER_OTLP_ENDPOINT is set. No-op otherwise."""
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        logger.info("op=observability status=disabled reason=no_endpoint")
        return

    resource = Resource.create({
        "service.name": "review-insight-backend",
        "service.version": os.environ.get("GIT_SHA", "dev"),
        "deployment.environment": os.environ.get("DEPLOY_ENV", "production"),
    })

    # Traces
    tracer_provider = TracerProvider(resource=resource)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces"))
    )
    trace.set_tracer_provider(tracer_provider)

    # Metrics
    metric_reader = PeriodicExportingMetricReader(
        OTLPMetricExporter(endpoint=f"{endpoint}/v1/metrics"),
        export_interval_millis=60_000,  # every 60s
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Auto-instrument
    FastAPIInstrumentor.instrument_app(app)
    SQLAlchemyInstrumentor().instrument(engine=db_engine)
    HTTPXClientInstrumentor().instrument()

    logger.info("op=observability status=enabled endpoint=%s", endpoint)
```

### 1.3 Custom business metrics

Add counters/histograms for things OTEL can't auto-detect:

```python
# In observability.py or a dedicated metrics.py
from opentelemetry import metrics

meter = metrics.get_meter("review-insight")

# Counters
reviews_fetched = meter.create_counter(
    "reviews.fetched", description="Total reviews fetched from providers"
)
analyses_run = meter.create_counter(
    "analyses.run", description="Total analysis runs"
)
comparisons_run = meter.create_counter(
    "comparisons.run", description="Total comparison runs"
)
comparison_cache_hits = meter.create_counter(
    "comparisons.cache_hits", description="Comparison cache hits (MongoDB)"
)
comparison_cache_misses = meter.create_counter(
    "comparisons.cache_misses", description="Comparison cache misses"
)
llm_errors = meter.create_counter(
    "llm.errors", description="LLM call failures"
)
llm_parse_failures = meter.create_counter(
    "llm.parse_failures", description="LLM returned invalid JSON"
)

# Histograms
llm_latency = meter.create_histogram(
    "llm.latency_ms", description="LLM call latency in milliseconds"
)
```

Where to increment them (one-line additions to existing code):

| Metric | File | Location |
|--------|------|----------|
| `reviews_fetched.add(len(reviews))` | `review_service.py` | After `fetch_reviews_for_business` returns |
| `analyses_run.add(1)` | `analysis_service.py` | After `_call_openai` succeeds |
| `llm_latency.record(duration_ms)` | `analysis_service.py` | Inside `timed_operation` for `llm_call` |
| `llm_errors.add(1)` | `analysis_service.py` | In the `except Exception` of `_call_openai` |
| `llm_parse_failures.add(1)` | `analysis_service.py` | In the `except JSONDecodeError` |
| `comparison_cache_hits.add(1)` | `comparison_service.py` | Where `logger.info("op=comparison_cache_hit")` is |
| `comparison_cache_misses.add(1)` | `comparison_service.py` | Before `_call_openai_comparison` |
| `comparisons_run.add(1)` | `comparison_service.py` | After comparison completes |

### 1.4 Wire into `main.py`

```python
# In create_app(), after app creation and before return:
from app.observability import init_observability
from app.database import engine
init_observability(app, engine)
```

### 1.5 Graceful degradation

Same pattern as MongoDB: if `OTEL_EXPORTER_OTLP_ENDPOINT` is unset, everything is a no-op. No code changes needed to run locally without observability.

### 1.6 Relationship to existing `tracing.py`

Keep `tracing.py` as-is for now. It's a debug tool (ring buffer, in-memory, dev-only). OTEL replaces it for production. Once OTEL is proven, you can deprecate the custom tracer — but that's a separate PR.

---

## Phase 2: Grafana Cloud Setup (Day 1)

### 2.1 Create Grafana Cloud account

1. Go to grafana.com → Create free account
2. A stack is auto-provisioned (includes Mimir, Loki, Tempo)
3. Go to **Connections → OpenTelemetry** → note the OTLP endpoint URL and API token

### 2.2 Store credentials in SSM Parameter Store

```bash
# The OTLP endpoint (e.g., https://otlp-gateway-prod-eu-west-0.grafana.net/otlp)
aws ssm put-parameter \
  --name "/review-insight/OTEL_EXPORTER_OTLP_ENDPOINT" \
  --value "https://otlp-gateway-prod-XX.grafana.net/otlp" \
  --type SecureString

# The API token (base64 of instance_id:api_key)
aws ssm put-parameter \
  --name "/review-insight/OTEL_EXPORTER_OTLP_HEADERS" \
  --value "Authorization=Basic <base64_token>" \
  --type SecureString
```

### 2.3 Add to ECS task definition

Add two new secrets to the container definition alongside existing MONGO_URI etc:

```json
{
  "name": "OTEL_EXPORTER_OTLP_ENDPOINT",
  "valueFrom": "/review-insight/OTEL_EXPORTER_OTLP_ENDPOINT"
},
{
  "name": "OTEL_EXPORTER_OTLP_HEADERS",
  "valueFrom": "/review-insight/OTEL_EXPORTER_OTLP_HEADERS"
}
```

---

## Phase 3: Dashboards (Day 2)

### 3.1 RED Dashboard (Request rate, Error rate, Duration)

Grafana dashboard with panels:

| Panel | Query (PromQL on OTEL metrics) | Purpose |
|-------|-------------------------------|---------|
| Request rate | `rate(http_server_request_duration_seconds_count[5m])` | Traffic volume |
| Error rate | `rate(http_server_request_duration_seconds_count{http_status_code=~"5.."}[5m])` | Server errors |
| P50/P95/P99 latency | `histogram_quantile(0.95, rate(http_server_request_duration_seconds_bucket[5m]))` | Slowdowns |
| LLM latency | `histogram_quantile(0.95, rate(llm_latency_ms_bucket[5m]))` | OpenAI performance |
| Cache hit ratio | `rate(comparisons_cache_hits_total[1h]) / (rate(comparisons_cache_hits_total[1h]) + rate(comparisons_cache_misses_total[1h]))` | MongoDB cache effectiveness |
| Error breakdown | Top 5 by `http_route` + `http_status_code` | Where errors cluster |

### 3.2 Business Metrics Dashboard

| Panel | Purpose |
|-------|---------|
| Reviews fetched/hour | Is the bot exercising the ingestion path? |
| Analyses run/hour | Are analyses completing? |
| Comparisons run/hour | Cache vs fresh |
| LLM parse failure rate | Is OpenAI returning garbage? |

### 3.3 Trace Explorer

Grafana Tempo's built-in trace explorer. Filter by:
- `service.name = review-insight-backend`
- `http.status_code >= 400` (find errors)
- Duration > 5s (find slow requests)

---

## Phase 4: Alerting → Phone (Day 2)

### 4.1 Telegram Bot Setup

1. Message `@BotFather` on Telegram → `/newbot` → name it `ReviewInsightAlerts`
2. Save the bot token
3. Send a message to your bot, then call `https://api.telegram.org/bot<TOKEN>/getUpdates` to get your `chat_id`

### 4.2 Grafana Alert Rules

Configure in Grafana Cloud → Alerting → Alert Rules:

| Alert | Condition | Severity | Why it matters |
|-------|-----------|----------|----------------|
| **High error rate** | 5xx rate > 5% for 5 min | Critical | Backend is broken |
| **Slow responses** | P95 latency > 10s for 5 min | Warning | Degraded experience |
| **LLM failures** | `llm.errors` > 3 in 10 min | Critical | OpenAI down or quota hit |
| **Bot health check failed** | No successful synthetic request in 30 min | Critical | App is down |
| **High LLM parse failure rate** | Parse failures > 20% of analyses in 1h | Warning | Model output quality degraded |
| **Zero traffic** | Request rate = 0 for 15 min | Warning | ECS task crashed or bot stopped |

### 4.3 Notification Channel

Grafana Cloud → Alerting → Contact Points → Add Telegram:
- Bot token: `<from BotFather>`
- Chat ID: `<your chat_id>`

Test it — you should get a ping on your phone.

---

## Phase 5: Synthetic Bot (Day 2-3)

### 5.1 Bot Script: `scripts/synthetic_monitor.py`

A Python script that exercises every user flow and reports results:

```python
"""Synthetic monitoring bot — exercises all user flows against live deployment."""

import os
import sys
import time
import httpx
import uuid
import json
from datetime import datetime, UTC

BASE_URL = os.environ.get("MONITOR_BASE_URL", "http://localhost:8000")
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

class SyntheticMonitor:
    def __init__(self):
        self.client = httpx.Client(base_url=f"{BASE_URL}/api", timeout=60)
        self.results = []
        self.token = None

    def _record(self, name, success, duration_ms, detail=""):
        self.results.append({
            "name": name,
            "success": success,
            "duration_ms": round(duration_ms),
            "detail": detail,
            "timestamp": datetime.now(UTC).isoformat(),
        })

    def _timed(self, name, fn):
        start = time.perf_counter()
        try:
            result = fn()
            duration = (time.perf_counter() - start) * 1000
            self._record(name, True, duration)
            return result
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            self._record(name, False, duration, str(e))
            return None

    def run(self):
        # 1. Health check
        self._timed("health_check", lambda: self._check(
            self.client.get("/health"), 200
        ))

        # 2. Register
        email = f"bot-{uuid.uuid4().hex[:8]}@synthetic.test"
        r = self._timed("register", lambda: self._check(
            self.client.post("/auth/register", json={
                "email": email, "password": "SyntheticBot123!"
            }), 201
        ))
        if r:
            self.token = r.json()["access_token"]

        if not self.token:
            self._send_alert("CRITICAL: Registration failed, aborting run")
            return self.results

        headers = {"Authorization": f"Bearer {self.token}"}

        # 3. Create business
        biz = self._timed("create_business", lambda: self._check(
            self.client.post("/businesses", json={
                "google_maps_url": "https://www.google.com/maps/place/Test/@0,0,17z/data=!4m2!3m1!1s0x0:0xBOT" + uuid.uuid4().hex[:6],
                "business_type": "restaurant",
            }, headers=headers), 201
        ))
        if not biz:
            self._send_alert("CRITICAL: Business creation failed")
            return self.results

        biz_id = biz.json()["id"]

        # 4. Fetch reviews (mock provider in non-prod)
        self._timed("fetch_reviews", lambda: self._check(
            self.client.post(f"/businesses/{biz_id}/fetch-reviews", headers=headers), 200
        ))

        # 5. Run analysis
        self._timed("analyze", lambda: self._check(
            self.client.post(f"/businesses/{biz_id}/analyze", headers=headers), 200
        ))

        # 6. Dashboard
        dash = self._timed("dashboard", lambda: self._check(
            self.client.get(f"/businesses/{biz_id}/dashboard", headers=headers), 200
        ))
        if dash:
            d = dash.json()
            if not d.get("ai_summary"):
                self._record("dashboard_completeness", False, 0, "ai_summary is null after analysis")

        # 7. Add competitor + comparison
        comp = self._timed("add_competitor", lambda: self._check(
            self.client.post(f"/businesses/{biz_id}/competitors", json={
                "google_maps_url": "https://www.google.com/maps/place/Comp/@0,0,17z/data=!4m2!3m1!1s0x0:0xCOMP" + uuid.uuid4().hex[:6],
                "business_type": "restaurant",
            }, headers=headers), 201
        ))

        if comp:
            comp_biz_id = comp.json()["business"]["id"]
            # Fetch + analyze competitor
            self._timed("fetch_competitor_reviews", lambda: self._check(
                self.client.post(f"/businesses/{comp_biz_id}/fetch-reviews", headers=headers), 200
            ))
            self._timed("analyze_competitor", lambda: self._check(
                self.client.post(f"/businesses/{comp_biz_id}/analyze", headers=headers), 200
            ))
            # Run comparison
            self._timed("comparison", lambda: self._check(
                self.client.post(f"/businesses/{biz_id}/competitors/comparison", headers=headers), 200
            ))
            # Run comparison again (should hit cache)
            self._timed("comparison_cached", lambda: self._check(
                self.client.post(f"/businesses/{biz_id}/competitors/comparison", headers=headers), 200
            ))

        # 8. Cleanup — delete business
        self._timed("delete_business", lambda: self._check(
            self.client.delete(f"/businesses/{biz_id}", headers=headers), 204
        ))

        # Report
        failures = [r for r in self.results if not r["success"]]
        if failures:
            self._send_alert(
                f"SYNTHETIC MONITOR: {len(failures)}/{len(self.results)} checks failed\n"
                + "\n".join(f"  - {f['name']}: {f['detail']}" for f in failures)
            )

        return self.results

    def _check(self, response, expected_status):
        if response.status_code != expected_status:
            raise ValueError(
                f"Expected {expected_status}, got {response.status_code}: "
                f"{response.text[:200]}"
            )
        return response

    def _send_alert(self, message):
        if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
            print(f"ALERT (no Telegram): {message}", file=sys.stderr)
            return
        try:
            httpx.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                json={"chat_id": TELEGRAM_CHAT_ID, "text": f"🔴 {message}"},
                timeout=10,
            )
        except Exception as e:
            print(f"Failed to send Telegram alert: {e}", file=sys.stderr)


if __name__ == "__main__":
    monitor = SyntheticMonitor()
    results = monitor.run()
    passed = sum(1 for r in results if r["success"])
    total = len(results)
    print(json.dumps({"passed": passed, "total": total, "results": results}, indent=2))
    sys.exit(0 if passed == total else 1)
```

### 5.2 GitHub Actions Cron Workflow: `.github/workflows/synthetic.yml`

```yaml
name: Synthetic Monitor

on:
  schedule:
    # Every 30 minutes during the observability experiment
    - cron: "*/30 * * * *"
  workflow_dispatch:  # Manual trigger for testing

jobs:
  monitor:
    name: Synthetic health check
    runs-on: ubuntu-latest
    env:
      MONITOR_BASE_URL: ${{ vars.BACKEND_PUBLIC_URL }}
      REVIEW_PROVIDER: mock
      TELEGRAM_BOT_TOKEN: ${{ secrets.TELEGRAM_BOT_TOKEN }}
      TELEGRAM_CHAT_ID: ${{ secrets.TELEGRAM_CHAT_ID }}

    steps:
      - uses: actions/checkout@v4

      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Install dependencies
        run: pip install httpx

      - name: Run synthetic monitor
        run: python scripts/synthetic_monitor.py

      - name: Upload results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: synthetic-results-${{ github.run_number }}
          path: /tmp/synthetic-results.json
          retention-days: 7
```

### 5.3 What the bot will exercise and find

| Flow | What could break | How we'd know |
|------|------------------|---------------|
| Register + login | Auth bugs, DB connection issues | 401/500 on register |
| Create business with Maps URL | Place ID parsing regression | 400 on create |
| Fetch reviews | Provider factory misconfigured | 500 on fetch |
| Analysis | OpenAI API changes, JSON schema drift | 502 or malformed dashboard |
| Dashboard after analysis | Missing fields, null where shouldn't be | Completeness check |
| Comparison (cold) | Competitor linking, snapshot building | 400/500 |
| Comparison (cached) | MongoDB cache key mismatch, TTL too short | Slower than expected or error |
| Delete business | Cascade delete bugs | 500 on delete |
| Repeated runs | User/business accumulation, DB bloat | Gradually slower responses |

---

## Phase 6: Cleanup After Experiment (Day 7-8)

### 6.1 What to keep

- `observability.py` module (production-ready, no-op when unconfigured)
- Custom metric counters in services (they're one-liners)
- Grafana dashboards (export as JSON, commit to `infrastructure/grafana/`)
- Synthetic monitor script (useful for ongoing CI)
- Alert rules (export as YAML)

### 6.2 What to tear down

- Disable the cron schedule in `synthetic.yml` (set `schedule: []` or comment out)
- Scale ECS to 0 if not needed
- Grafana Cloud free tier has no cost — can leave running

### 6.3 Cleanup synthetic data

The bot creates and deletes businesses each run, but users accumulate. Add a cleanup step or a TTL on bot-created users (email pattern `bot-*@synthetic.test`).

---

## Cost Breakdown

| Component | Cost |
|-----------|------|
| Grafana Cloud free tier | $0 |
| GitHub Actions cron (48 runs/day × 7 days) | ~17 min total → $0 (well within free tier) |
| Telegram bot | $0 |
| AWS ECS Fargate (already running) | Existing cost |
| OpenAI API (mock provider for bot) | $0 if REVIEW_PROVIDER=mock; ~$0.50 if using real OpenAI |
| **Total** | **$0 - $0.50** |

---

## Implementation Order

```
Day 1 (2-3 hours):
  ├── Add OTEL dependencies to requirements.txt
  ├── Create observability.py
  ├── Add metric counters to services (one-liners)
  ├── Wire into main.py
  ├── Create Grafana Cloud account
  ├── Store OTEL creds in SSM Parameter Store
  ├── Update ECS task def with OTEL env vars
  └── Deploy and verify traces appear in Grafana

Day 2 (2-3 hours):
  ├── Build RED dashboard in Grafana
  ├── Build business metrics dashboard
  ├── Set up Telegram bot via BotFather
  ├── Configure alert rules in Grafana
  ├── Test alerts (trigger a 500, verify phone ping)
  ├── Write synthetic_monitor.py
  ├── Create synthetic.yml workflow
  └── Manual trigger to verify bot works

Day 3-7:
  ├── Bot runs every 30 min automatically
  ├── Monitor dashboards for anomalies
  ├── Investigate any alerts
  └── Document bugs found

Day 7-8:
  ├── Export dashboards + alert rules
  ├── Disable cron schedule
  ├── Write findings summary
  └── Update CV/interview prep with observability story
```

---

## Interview Angle

This is a strong story for interviews because:

1. **You chose OpenTelemetry** (industry standard) over custom solutions or vendor lock-in
2. **Grafana Cloud** shows you know the LGTM stack (Loki, Grafana, Tempo, Mimir)
3. **Synthetic monitoring** demonstrates you think about reliability, not just features
4. **Alert design** shows you understand which failures matter (not just "alert on everything")
5. **Budget awareness** — you picked a $0 solution that works at scale. This is what real teams do.
6. **Graceful degradation** — same pattern as MongoDB: OTEL no-ops when unconfigured

The question they'll ask: "How did you monitor your application in production?"

Your answer: "I instrumented with OpenTelemetry, exported to Grafana Cloud, built RED dashboards and business metric dashboards, set up Telegram alerts for error spikes and LLM failures, and ran a synthetic bot every 30 minutes for a week. It caught [specific bug X] on day 3."

That last sentence — the specific bug — is what separates "I set up monitoring" from "I used monitoring to find and fix a real problem."
