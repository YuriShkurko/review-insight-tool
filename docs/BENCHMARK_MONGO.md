# Polyglot Persistence Benchmark

> Auto-generated on 2026-04-12T07:20:58Z | Mode: **Postgres + MongoDB** | Iterations: 3 | Reviews: 100

## Results

| Operation | Avg (ms) | Min (ms) | Max (ms) | Std Dev |
|-----------|----------|----------|----------|---------|
| analysis_first | 11244.3 | 11244.3 | 11244.3 | 0.0 |
| analysis_rerun | 9124.7 | 8148.6 | 10100.9 | 1380.5 |
| history_query | 575.5 | 570.6 | 584.8 | 8.0 |
| comparison_cold | 5189.7 | 5189.7 | 5189.7 | 0.0 |
| comparison_cached | 1234.7 | 1229.1 | 1239.5 | 5.2 |

## Speedup Analysis

- **Comparison cache speedup:** 4.2x (cold 5190ms vs cached 1235ms)
- **Cache mechanism:** MongoDB document lookup (skips LLM call entirely)
- **Analysis archive overhead:** -2120ms (first 11244ms vs re-run 9125ms)
- **History query latency:** 575ms avg

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
