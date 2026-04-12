#!/usr/bin/env python3
"""Polyglot Persistence Benchmark — Postgres-only vs Postgres+MongoDB.

Runs against a live backend (default http://localhost:8000) using the offline
(mock) review provider.  Measures latency for analysis, analysis history,
and comparison (cold + cached) operations.

Outputs docs/BENCHMARK.md with a results table and speedup analysis.

Usage:
    # Start the stack first:
    make up                              # Postgres-only baseline
    make up MONGO_URI=mongodb://mongo:27017  # With MongoDB

    python -m scripts.benchmark_mongo          # from backend/
    python -m scripts.benchmark_mongo --iterations 5
    python -m scripts.benchmark_mongo --base-url http://my-host:8000
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import httpx

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")
API_PREFIX = "/api"
ITERATIONS = 3


# ── Data structures ────────────────────────────────────────────


@dataclass
class TimingResult:
    name: str
    times_ms: list[float] = field(default_factory=list)

    @property
    def avg(self) -> float:
        return statistics.mean(self.times_ms) if self.times_ms else 0

    @property
    def min(self) -> float:
        return min(self.times_ms) if self.times_ms else 0

    @property
    def max(self) -> float:
        return max(self.times_ms) if self.times_ms else 0

    @property
    def stdev(self) -> float:
        return statistics.stdev(self.times_ms) if len(self.times_ms) > 1 else 0


# ── Helpers ────────────────────────────────────────────────────


def timed_request(
    client: httpx.Client,
    method: str,
    url: str,
    headers: dict,
    **kwargs,
) -> tuple[httpx.Response, float]:
    """Execute an HTTP request and return (response, elapsed_ms)."""
    start = time.perf_counter()
    resp = client.request(method, url, headers=headers, **kwargs)
    elapsed = (time.perf_counter() - start) * 1000
    return resp, elapsed


def fail(msg: str) -> None:
    print(f"\nFATAL: {msg}", file=sys.stderr)
    sys.exit(1)


# ── Benchmark flow ─────────────────────────────────────────────


def run_benchmark(base_url: str, iterations: int) -> dict:
    """Execute the full benchmark and return results dict."""
    api = f"{base_url}{API_PREFIX}"
    tag = uuid.uuid4().hex[:8]
    results: dict[str, TimingResult] = {}

    def record(name: str) -> TimingResult:
        if name not in results:
            results[name] = TimingResult(name=name)
        return results[name]

    with httpx.Client(base_url=api, timeout=60) as c:
        # ── 1. Register benchmark user ──
        email = f"bench-{tag}@test.com"
        r = c.post("/auth/register", json={"email": email, "password": "bench1234"})
        if r.status_code != 201:
            fail(f"Register failed: {r.text}")
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        print(f"  Registered benchmark user: {email}")

        # ── 2. Create target business (offline/mock) ──
        r = c.post(
            "/businesses",
            json={
                "place_id": "offline_lager_ale",
                "business_type": "bar",
            },
            headers=h,
        )
        if r.status_code != 201:
            fail(f"Create target business failed: {r.text}")
        target_id = r.json()["id"]
        print(f"  Created target business: {r.json()['name']} ({target_id})")

        # ── 3. Fetch reviews for target ──
        r = c.post(f"/businesses/{target_id}/fetch-reviews", headers=h)
        if r.status_code != 200:
            fail(f"Fetch reviews failed: {r.text}")
        review_count = len(r.json())
        print(f"  Fetched {review_count} reviews for target")

        # ── 4-5. Analysis benchmarks ──
        for i in range(iterations):
            label = "analysis_first" if i == 0 else "analysis_rerun"
            r, elapsed = timed_request(c, "POST", f"/businesses/{target_id}/analyze", h)
            if r.status_code != 200:
                fail(f"Analyze failed (iter {i}): {r.text}")
            record(label).times_ms.append(elapsed)
            print(f"  Analysis iter {i}: {elapsed:.1f}ms ({label})")

        # ── 6. Analysis history query (requires MongoDB endpoint) ──
        for i in range(iterations):
            r, elapsed = timed_request(
                c,
                "GET",
                f"/businesses/{target_id}/analysis-history",
                h,
                params={"business_id": target_id},
            )
            if r.status_code == 404:
                print(f"  History query: endpoint not available (pre-MongoDB baseline)")
                break
            if r.status_code != 200:
                fail(f"Analysis history failed: {r.text}")
            history_count = len(r.json())
            record("history_query").times_ms.append(elapsed)
            print(f"  History query iter {i}: {elapsed:.1f}ms ({history_count} versions)")

        # ── 7. Create competitor business ──
        r = c.post(
            f"/businesses/{target_id}/competitors",
            json={
                "place_id": "offline_beer_garden",
                "business_type": "bar",
            },
            headers=h,
        )
        if r.status_code != 201:
            fail(f"Add competitor failed: {r.text}")
        comp_biz = r.json()["business"]
        comp_id = comp_biz["id"]
        print(f"  Added competitor: {comp_biz['name']} ({comp_id})")

        # ── 8. Fetch reviews for competitor ──
        r = c.post(f"/businesses/{comp_id}/fetch-reviews", headers=h)
        if r.status_code != 200:
            fail(f"Fetch competitor reviews failed: {r.text}")
        print(f"  Fetched {len(r.json())} reviews for competitor")

        # ── 9. Run analysis on competitor ──
        r = c.post(f"/businesses/{comp_id}/analyze", headers=h)
        if r.status_code != 200:
            fail(f"Analyze competitor failed: {r.text}")
        print(f"  Analyzed competitor")

        # ── 10. Comparison (cold — hits LLM) ──
        r, elapsed = timed_request(
            c, "POST", f"/businesses/{target_id}/competitors/comparison", h
        )
        if r.status_code != 200:
            fail(f"Comparison (cold) failed: {r.text}")
        record("comparison_cold").times_ms.append(elapsed)
        print(f"  Comparison cold: {elapsed:.1f}ms")

        # ── 11-12. Comparison (cached — MongoDB or LLM fallback) ──
        for i in range(iterations):
            r, elapsed = timed_request(
                c, "POST", f"/businesses/{target_id}/competitors/comparison", h
            )
            if r.status_code != 200:
                fail(f"Comparison (cached iter {i}) failed: {r.text}")
            record("comparison_cached").times_ms.append(elapsed)
            print(f"  Comparison cached iter {i}: {elapsed:.1f}ms")

    return {
        "results": results,
        "meta": {
            "base_url": base_url,
            "iterations": iterations,
            "review_count": review_count,
            "tag": tag,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
    }


# ── Markdown report ────────────────────────────────────────────


def generate_report(data: dict, mongo_enabled: bool) -> str:
    results: dict[str, TimingResult] = data["results"]
    meta = data["meta"]
    mode = "Postgres + MongoDB" if mongo_enabled else "Postgres-only"

    lines = [
        "# Polyglot Persistence Benchmark",
        "",
        f"> Auto-generated on {meta['timestamp'][:19]}Z | "
        f"Mode: **{mode}** | "
        f"Iterations: {meta['iterations']} | "
        f"Reviews: {meta['review_count']}",
        "",
        "## Results",
        "",
        "| Operation | Avg (ms) | Min (ms) | Max (ms) | Std Dev |",
        "|-----------|----------|----------|----------|---------|",
    ]

    order = [
        "analysis_first",
        "analysis_rerun",
        "history_query",
        "comparison_cold",
        "comparison_cached",
    ]

    for name in order:
        r = results.get(name)
        if not r:
            continue
        lines.append(
            f"| {name} | {r.avg:.1f} | {r.min:.1f} | {r.max:.1f} | {r.stdev:.1f} |"
        )

    lines.append("")

    # Speedup analysis
    cold = results.get("comparison_cold")
    cached = results.get("comparison_cached")
    if cold and cached and cached.avg > 0:
        speedup = cold.avg / cached.avg
        lines.extend([
            "## Speedup Analysis",
            "",
            f"- **Comparison cache speedup:** {speedup:.1f}x "
            f"(cold {cold.avg:.0f}ms vs cached {cached.avg:.0f}ms)",
        ])
        if mongo_enabled:
            lines.append(
                "- **Cache mechanism:** MongoDB document lookup (skips LLM call entirely)"
            )
        else:
            lines.append(
                "- **Cache mechanism:** None (Postgres-only — every comparison hits the LLM)"
            )

    first = results.get("analysis_first")
    rerun = results.get("analysis_rerun")
    if first and rerun:
        overhead = rerun.avg - first.avg
        lines.extend([
            f"- **Analysis archive overhead:** {overhead:+.0f}ms "
            f"(first {first.avg:.0f}ms vs re-run {rerun.avg:.0f}ms)",
        ])

    history = results.get("history_query")
    if history:
        lines.append(f"- **History query latency:** {history.avg:.0f}ms avg")

    lines.extend([
        "",
        "## Architecture",
        "",
        "```",
        "                  +-- Postgres (source of truth) --+",
        "                  |   users, businesses, reviews,  |",
        "  FastAPI ------->|   analyses, competitor_links    |",
        "                  +--------------------------------+",
        "                  |                                 |",
        "                  +-- MongoDB (optional speed layer)+",
        "                  |   comparison_cache   (TTL 24h)  |",
        "                  |   analysis_history   (permanent)|",
        "                  |   raw_provider_responses (30d)  |",
        "                  +--------------------------------+",
        "```",
        "",
        "Postgres remains the single source of truth. MongoDB accelerates",
        "read-heavy operations (comparison cache hits skip the LLM call",
        "entirely) and stores data that doesn't fit the relational model",
        "(versioned analysis history, raw API payloads).",
        "",
    ])

    return "\n".join(lines)


# ── CLI ────────────────────────────────────────────────────────


def main() -> None:
    parser = argparse.ArgumentParser(description="Polyglot Persistence Benchmark")
    parser.add_argument(
        "--base-url", default=BASE_URL, help=f"Backend URL (default: {BASE_URL})"
    )
    parser.add_argument(
        "--iterations", type=int, default=ITERATIONS, help=f"Iterations per scenario (default: {ITERATIONS})"
    )
    parser.add_argument(
        "--mongo", action="store_true", default=False,
        help="Flag indicating MongoDB is enabled (affects report labels)",
    )
    parser.add_argument(
        "--output", default=None,
        help="Output path for BENCHMARK.md (default: docs/BENCHMARK.md relative to repo root)",
    )
    args = parser.parse_args()

    print(f"\n{'='*60}")
    print(f"  Polyglot Persistence Benchmark")
    print(f"  Backend: {args.base_url}")
    print(f"  Iterations: {args.iterations}")
    print(f"  MongoDB: {'enabled' if args.mongo else 'disabled (baseline)'}")
    print(f"{'='*60}\n")

    data = run_benchmark(args.base_url, args.iterations)

    report = generate_report(data, mongo_enabled=args.mongo)

    # Determine output path
    if args.output:
        out_path = Path(args.output)
    else:
        # Navigate from backend/scripts/ up to repo root
        repo_root = Path(__file__).resolve().parent.parent.parent
        out_path = repo_root / "docs" / "BENCHMARK.md"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report, encoding="utf-8")
    print(f"\nReport written to {out_path}")

    # Print summary to stdout
    print(f"\n{'='*60}")
    print("  Summary")
    print(f"{'='*60}")
    for name in ["analysis_first", "analysis_rerun", "history_query", "comparison_cold", "comparison_cached"]:
        r = data["results"].get(name)
        if r:
            print(f"  {name:25s}  avg={r.avg:8.1f}ms  min={r.min:8.1f}ms  max={r.max:8.1f}ms")
    print()


if __name__ == "__main__":
    main()
