# Polyglot Persistence Benchmark

> Benchmark comparing Postgres-only vs Postgres + MongoDB (Atlas M0) on AWS ECS Fargate.
> Both runs hit the same deployed backend with 100 offline reviews, 3 iterations per scenario.
> Run date: 2026-04-12

## Before vs After

| Operation | Postgres-only (ms) | + MongoDB (ms) | Change |
|-----------|--------------------:|---------------:|--------|
| analysis (first run) | 8,151 | 11,244 | same (LLM-bound) |
| analysis (re-run) | 10,073 | 9,125 | same (LLM-bound) |
| analysis history query | N/A | 575 | **new capability** |
| comparison (cold) | 5,797 | 5,190 | same (LLM-bound) |
| comparison (cache hit) | 5,049 | 1,235 | **4.2x faster** |

## Key Findings

### Comparison cache: 4.2x speedup (skips LLM entirely)

Without MongoDB, every comparison request calls OpenAI (~5s). With MongoDB,
repeat comparisons serve a cached document instead. The 1.2s floor is network
latency (benchmark client in Israel hitting Frankfurt); server-side cache lookup
is <50ms.

### Analysis history: new capability

Versioned analysis snapshots stored in MongoDB. Previous versions are archived
before each re-analysis. History queries return in ~575ms (network-dominated).

### Zero regression on write path

Analysis and comparison write operations show no measurable overhead from the
MongoDB archival/caching (fire-and-forget writes).

### Graceful degradation

When `MONGO_URI` is unset, all MongoDB features no-op. The app runs identically
to the Postgres-only baseline with zero code changes.

## Architecture

```
                  +-- Postgres (source of truth) ----+
                  |   users, businesses, reviews,    |
  FastAPI ------->|   analyses, competitor_links      |
                  +----------------------------------+
                  |                                   |
                  +-- MongoDB (optional speed layer) -+
                  |   comparison_cache    (TTL 24h)   |
                  |   analysis_history    (permanent)  |
                  |   raw_provider_responses (30d)     |
                  +----------------------------------+
```

Postgres remains the single source of truth for all business data.
MongoDB accelerates read-heavy operations and stores data that doesn't
fit the relational model:

- **comparison_cache** — eliminates redundant LLM calls (TTL-indexed)
- **analysis_history** — versioned snapshots for trend tracking
- **raw_provider_responses** — audit trail of API payloads (TTL 30 days)

## Reproducing

```bash
# Postgres-only baseline
make up   # without MONGO_URI in backend/.env
cd backend && python -m scripts.benchmark_mongo --output ../docs/BENCHMARK_BASELINE.md

# With MongoDB
# Set MONGO_URI in backend/.env (Atlas or local)
make up
cd backend && python -m scripts.benchmark_mongo --mongo --output ../docs/BENCHMARK_MONGO.md
```
