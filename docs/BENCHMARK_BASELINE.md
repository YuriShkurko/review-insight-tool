# Polyglot Persistence Benchmark

> Auto-generated on 2026-04-12T06:49:39Z | Mode: **Postgres-only** | Iterations: 3 | Reviews: 100

## Results

| Operation | Avg (ms) | Min (ms) | Max (ms) | Std Dev |
|-----------|----------|----------|----------|---------|
| analysis_first | 8150.6 | 8150.6 | 8150.6 | 0.0 |
| analysis_rerun | 10073.0 | 7995.8 | 12150.1 | 2937.6 |
| comparison_cold | 5797.0 | 5797.0 | 5797.0 | 0.0 |
| comparison_cached | 5048.5 | 4574.8 | 5397.0 | 425.2 |

## Speedup Analysis

- **Comparison cache speedup:** 1.1x (cold 5797ms vs cached 5048ms)
- **Cache mechanism:** None (Postgres-only — every comparison hits the LLM)
- **Analysis archive overhead:** +1922ms (first 8151ms vs re-run 10073ms)

## Architecture

```
                  +-- Postgres (source of truth) --+
                  |   users, businesses, reviews,  |
  FastAPI ------->|   analyses, competitor_links    |
                  +--------------------------------+
                  |                                 |
                  +-- MongoDB (optional speed layer)+
                  |   comparison_cache   (TTL 24h)  |
                  |   analysis_history   (permanent)|
                  |   raw_provider_responses (30d)  |
                  +--------------------------------+
```

Postgres remains the single source of truth. MongoDB accelerates
read-heavy operations (comparison cache hits skip the LLM call
entirely) and stores data that doesn't fit the relational model
(versioned analysis history, raw API payloads).
