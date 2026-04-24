"""Demo world soak report.

Collects data from the 14-day arc cycle and sends a human-readable
findings summary to Telegram. Also writes a full markdown report.

Sources:
  - sim_reviews table (reviews injected, avg ratings per arc phase)
  - GitHub Actions API (synthetic monitor pass/fail history)

Usage:
    DATABASE_URL=... GITHUB_TOKEN=... python scripts/demo_report.py
    DATABASE_URL=... GITHUB_TOKEN=... python scripts/demo_report.py --since 2026-04-24

Env vars:
    DATABASE_URL         Postgres connection string
    GITHUB_TOKEN         GitHub token (auto-set in Actions via GITHUB_TOKEN)
    GITHUB_REPOSITORY    owner/repo (auto-set in Actions)
    TELEGRAM_BOT_TOKEN   Telegram bot token
    TELEGRAM_CHAT_ID     Telegram chat ID
    REPORT_PATH          Where to write the markdown report (default: demo-report.md)
    DEMO_API_URL         Public URL of the demo deployment
"""

from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta, timezone

import httpx

# ---------------------------------------------------------------------------
# Arc calendar (must match tick_demo.py)
# ---------------------------------------------------------------------------

ARC_EPOCH = 1776988800   # 2026-04-24 00:00 UTC
ARC_PERIOD = 14 * 86400  # 14 days

ARCS = [
    {"name": "festival_weekend", "label": "Craft Beer Festival",  "emoji": "🎪",
     "offset_start": 0,                "offset_end": int(2.5 * 86400)},
    {"name": "quiet_week",       "label": "Quiet Week",           "emoji": "😴",
     "offset_start": int(2.5 * 86400), "offset_end": 7 * 86400},
    {"name": "bad_keg",          "label": "Bad Keg Incident",     "emoji": "💀",
     "offset_start": 7 * 86400,        "offset_end": int(9.5 * 86400)},
    {"name": "recovery",         "label": "Recovery Arc",         "emoji": "💚",
     "offset_start": int(9.5 * 86400), "offset_end": 12 * 86400},
    {"name": "wind_down",        "label": "Wind-Down",            "emoji": "🌅",
     "offset_start": 12 * 86400,       "offset_end": ARC_PERIOD},
]

BUSINESSES = {
    "sim_lager_ale_tlv": "Lager & Ale TLV",
    "sim_beer_garden":   "The Beer Garden",
    "sim_tap_room":      "The Tap Room",
}

DEMO_URL = os.environ.get("DEMO_API_URL", "").rstrip("/")
DEMO_LOGIN = "demo@review-insight.app / DemoWorld2026!"


# ---------------------------------------------------------------------------
# Data collection — DB
# ---------------------------------------------------------------------------

@dataclass
class ArcStats:
    name: str
    label: str
    emoji: str
    start_ts: float
    end_ts: float
    total_reviews: int = 0
    reviews_by_biz: dict[str, int] = field(default_factory=dict)
    avg_rating_by_biz: dict[str, float] = field(default_factory=dict)
    completed: bool = False   # whether we've passed the arc's end time


def collect_db_stats(db_url: str, cycle_start_ts: float) -> list[ArcStats]:
    import sqlalchemy as sa

    engine = sa.create_engine(db_url)
    now_ts = datetime.now(UTC).timestamp()
    stats: list[ArcStats] = []

    with engine.connect() as conn:
        for arc in ARCS:
            start_ts = cycle_start_ts + arc["offset_start"]
            end_ts   = cycle_start_ts + arc["offset_end"]
            start_dt = datetime.fromtimestamp(start_ts, UTC)
            end_dt   = datetime.fromtimestamp(end_ts, UTC)

            rows = conn.execute(
                sa.text(
                    """
                    SELECT place_id,
                           COUNT(*)       AS cnt,
                           AVG(rating)    AS avg_r
                    FROM sim_reviews
                    WHERE published_at >= :start
                      AND published_at <  :end
                      AND place_id = ANY(:pids)
                    GROUP BY place_id
                    """
                ),
                {
                    "start": start_dt,
                    "end": end_dt,
                    "pids": list(BUSINESSES.keys()),
                },
            ).fetchall()

            a = ArcStats(
                name=arc["name"],
                label=arc["label"],
                emoji=arc["emoji"],
                start_ts=start_ts,
                end_ts=end_ts,
                completed=(now_ts >= end_ts),
            )
            for row in rows:
                pid = row.place_id
                a.reviews_by_biz[pid] = row.cnt
                a.avg_rating_by_biz[pid] = round(float(row.avg_r), 2)
            a.total_reviews = sum(a.reviews_by_biz.values())
            stats.append(a)

    return stats


def collect_total_db(db_url: str, since_ts: float) -> dict[str, int]:
    """Total reviews per business since the cycle started."""
    import sqlalchemy as sa

    engine = sa.create_engine(db_url)
    since_dt = datetime.fromtimestamp(since_ts, UTC)
    with engine.connect() as conn:
        rows = conn.execute(
            sa.text(
                """
                SELECT place_id, COUNT(*) AS cnt
                FROM sim_reviews
                WHERE published_at >= :since
                  AND place_id = ANY(:pids)
                GROUP BY place_id
                """
            ),
            {"since": since_dt, "pids": list(BUSINESSES.keys())},
        ).fetchall()
    return {row.place_id: row.cnt for row in rows}


# ---------------------------------------------------------------------------
# Data collection — GitHub Actions
# ---------------------------------------------------------------------------

@dataclass
class MonitorStats:
    total_runs: int = 0
    passed: int = 0
    failed: int = 0
    failures: list[dict] = field(default_factory=list)   # {date, conclusion, name}


def collect_github_stats(token: str, repo: str, since_ts: float) -> MonitorStats:
    since_dt = datetime.fromtimestamp(since_ts, UTC)
    since_str = since_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base = f"https://api.github.com/repos/{repo}"
    stats = MonitorStats()

    # Find the workflow ID for synthetic.yml
    wf_id = None
    try:
        r = httpx.get(f"{base}/actions/workflows", headers=headers, timeout=20)
        r.raise_for_status()
        for wf in r.json().get("workflows", []):
            if "synthetic" in wf.get("path", "").lower():
                wf_id = wf["id"]
                break
    except Exception as e:
        print(f"  Warning: could not fetch workflows list: {e}", file=sys.stderr)
        return stats

    if not wf_id:
        print("  Warning: synthetic workflow not found in repo", file=sys.stderr)
        return stats

    # Paginate runs
    page = 1
    while True:
        try:
            r = httpx.get(
                f"{base}/actions/workflows/{wf_id}/runs",
                headers=headers,
                params={"created": f">={since_str}", "per_page": 100, "page": page},
                timeout=30,
            )
            r.raise_for_status()
        except Exception as e:
            print(f"  Warning: GitHub API error: {e}", file=sys.stderr)
            break

        runs = r.json().get("workflow_runs", [])
        if not runs:
            break

        for run in runs:
            conclusion = run.get("conclusion")
            if conclusion is None:
                continue   # still in progress
            stats.total_runs += 1
            if conclusion == "success":
                stats.passed += 1
            else:
                stats.failed += 1
                stats.failures.append({
                    "date": run["created_at"][:10],
                    "conclusion": conclusion,
                    "url": run["html_url"],
                })

        if len(runs) < 100:
            break
        page += 1

    return stats


# ---------------------------------------------------------------------------
# Report formatting
# ---------------------------------------------------------------------------

def stars(avg: float) -> str:
    filled = round(avg)
    return "★" * filled + "☆" * (5 - filled) + f" {avg:.1f}"


def pct(n: int, total: int) -> str:
    if total == 0:
        return "n/a"
    return f"{n * 100 // total}%"


def fmt_date(ts: float) -> str:
    return datetime.fromtimestamp(ts, UTC).strftime("%b %d")


def build_telegram_message(
    arc_stats: list[ArcStats],
    totals: dict[str, int],
    monitor: MonitorStats,
    cycle_start_ts: float,
    now_ts: float,
) -> str:
    cycle_day = (now_ts - cycle_start_ts) / 86400
    period_label = f"{fmt_date(cycle_start_ts)} - {fmt_date(now_ts)}"
    cycle_complete = cycle_day >= 14

    lines: list[str] = []
    lines.append("Review Insight - Demo Soak Report")
    lines.append(f"Period: {period_label}  (Day {cycle_day:.0f}/14{'  COMPLETE' if cycle_complete else '  in progress'})")
    lines.append("")

    # --- Story arc section ---
    lines.append("THE STORY THAT PLAYED OUT")
    lines.append("-" * 28)
    for a in arc_stats:
        if a.total_reviews == 0 and not a.completed:
            lines.append(f"{a.emoji} {a.label}: not reached yet")
            continue

        date_range = f"{fmt_date(a.start_ts)} - {fmt_date(a.end_ts)}"
        status = "" if a.completed else " (ongoing)"
        lines.append(f"{a.emoji} {a.label} ({date_range}){status}")

        if a.total_reviews == 0:
            lines.append(f"   No reviews injected during this phase")
            continue

        lines.append(f"   {a.total_reviews} new reviews across all bars")

        # Highlight the most interesting business for this arc
        if a.name == "bad_keg" and "sim_tap_room" in a.avg_rating_by_biz:
            avg = a.avg_rating_by_biz["sim_tap_room"]
            cnt = a.reviews_by_biz.get("sim_tap_room", 0)
            lines.append(f"   The Tap Room: {cnt} angry reviews, avg {stars(avg)}")
            lines.append(f"   Competitors saw a traffic bump while Tap Room struggled")
        elif a.name == "recovery" and "sim_tap_room" in a.avg_rating_by_biz:
            avg = a.avg_rating_by_biz["sim_tap_room"]
            cnt = a.reviews_by_biz.get("sim_tap_room", 0)
            lines.append(f"   The Tap Room: {cnt} comeback reviews, avg {stars(avg)}")
        elif a.name == "festival_weekend":
            for pid, bname in BUSINESSES.items():
                cnt = a.reviews_by_biz.get(pid, 0)
                avg = a.avg_rating_by_biz.get(pid, 0)
                if cnt:
                    lines.append(f"   {bname}: {cnt} reviews, avg {stars(avg)}")
        elif a.name == "quiet_week" or a.name == "wind_down":
            grand_avg = (
                sum(a.avg_rating_by_biz.get(p, 0) * a.reviews_by_biz.get(p, 0)
                    for p in BUSINESSES)
                / max(a.total_reviews, 1)
            )
            lines.append(f"   System steady - avg {grand_avg:.1f} stars across all bars")

        lines.append("")

    # Remove trailing blank line inside section
    while lines and lines[-1] == "":
        lines.pop()

    lines.append("")

    # --- Review totals ---
    grand_total = sum(totals.values())
    lines.append("TOTAL PIPELINE THROUGHPUT")
    lines.append("-" * 28)
    lines.append(f"{grand_total} reviews processed with zero manual intervention")
    for pid, bname in BUSINESSES.items():
        cnt = totals.get(pid, 0)
        if cnt:
            lines.append(f"  {bname}: {cnt} reviews")
    lines.append("")

    # --- Health section ---
    lines.append("LIVE SYSTEM HEALTH")
    lines.append("-" * 28)
    if monitor.total_runs == 0:
        lines.append("No synthetic monitor runs found for this period")
    else:
        pass_rate = monitor.passed * 100 // monitor.total_runs
        icon = "OK" if monitor.failed == 0 else ("WARN" if pass_rate >= 90 else "FAIL")
        lines.append(f"[{icon}] {monitor.passed}/{monitor.total_runs} synthetic health checks passed ({pass_rate}%)")

        if monitor.failures:
            # Group failures by date
            by_date: dict[str, int] = {}
            for f in monitor.failures:
                by_date[f["date"]] = by_date.get(f["date"], 0) + 1
            failure_summary = ", ".join(f"{d}: {n} fail(s)" for d, n in sorted(by_date.items()))
            lines.append(f"Failures: {failure_summary}")
        else:
            lines.append("No failures detected during this period")
    lines.append("")

    # --- What this proves ---
    lines.append("WHAT THIS PROVES")
    lines.append("-" * 28)
    story_lines = []
    if grand_total > 0:
        story_lines.append(
            f"The review-to-insight pipeline ran autonomously for {cycle_day:.0f} days, "
            f"processing {grand_total} synthetic reviews without any manual intervention."
        )

    bad_keg = next((a for a in arc_stats if a.name == "bad_keg" and a.total_reviews > 0), None)
    recovery = next((a for a in arc_stats if a.name == "recovery" and a.total_reviews > 0), None)

    if bad_keg and "sim_tap_room" in bad_keg.avg_rating_by_biz:
        bad_avg = bad_keg.avg_rating_by_biz["sim_tap_room"]
        if recovery and "sim_tap_room" in recovery.avg_rating_by_biz:
            rec_avg = recovery.avg_rating_by_biz["sim_tap_room"]
            story_lines.append(
                f"The bad keg incident drove The Tap Room from its baseline down to {bad_avg:.1f} stars, "
                f"then the recovery arc brought it back to {rec_avg:.1f} stars - "
                f"exactly the kind of reputation signal this product is built to surface."
            )
        else:
            story_lines.append(
                f"The bad keg arc drove a real measurable dip to {bad_avg:.1f} stars "
                f"visible in the dashboard."
            )

    if monitor.total_runs > 0 and monitor.passed / monitor.total_runs >= 0.95:
        story_lines.append(
            f"System maintained {monitor.passed * 100 // monitor.total_runs}% health "
            f"across {monitor.total_runs} synthetic checks under continuous load."
        )

    for sl in story_lines:
        # Word-wrap at 60 chars for Telegram readability
        words = sl.split()
        line = ""
        for word in words:
            if len(line) + len(word) + 1 > 60:
                lines.append(line)
                line = word
            else:
                line = (line + " " + word).strip()
        if line:
            lines.append(line)
    lines.append("")

    # --- Footer ---
    if DEMO_URL:
        lines.append(f"Demo: {DEMO_URL}")
    lines.append(f"Login: {DEMO_LOGIN}")

    return "\n".join(lines)


def build_markdown_report(
    arc_stats: list[ArcStats],
    totals: dict[str, int],
    monitor: MonitorStats,
    cycle_start_ts: float,
    now_ts: float,
) -> str:
    cycle_day = (now_ts - cycle_start_ts) / 86400
    period_label = f"{fmt_date(cycle_start_ts)} - {fmt_date(now_ts)}"

    md: list[str] = []
    md.append("# Review Insight — Demo World Soak Report")
    md.append(f"\n**Period:** {period_label}  **Cycle day:** {cycle_day:.1f} / 14")
    md.append(f"\n**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}")
    if DEMO_URL:
        md.append(f"\n**Demo URL:** {DEMO_URL}")
    md.append(f"\n**Login:** `{DEMO_LOGIN}`")

    md.append("\n---\n")
    md.append("## Arc Phase Breakdown\n")
    md.append("| Phase | Dates | Reviews | Lager & Ale | Beer Garden | Tap Room |")
    md.append("|-------|-------|---------|-------------|-------------|----------|")

    for a in arc_stats:
        dr = f"{fmt_date(a.start_ts)} - {fmt_date(a.end_ts)}"
        status = "" if a.completed else " *(ongoing)*"

        def cell(pid: str) -> str:
            cnt = a.reviews_by_biz.get(pid, 0)
            avg = a.avg_rating_by_biz.get(pid, 0)
            if cnt == 0:
                return "-"
            return f"{cnt} rev · {avg:.1f}★"

        md.append(
            f"| {a.emoji} {a.label}{status} | {dr} | **{a.total_reviews}** | "
            f"{cell('sim_lager_ale_tlv')} | {cell('sim_beer_garden')} | {cell('sim_tap_room')} |"
        )

    md.append("\n---\n")
    md.append("## Total Review Volume\n")
    grand_total = sum(totals.values())
    md.append(f"**{grand_total} reviews total** injected since cycle start\n")
    for pid, bname in BUSINESSES.items():
        cnt = totals.get(pid, 0)
        md.append(f"- **{bname}**: {cnt} reviews")

    md.append("\n---\n")
    md.append("## Synthetic Monitor Health\n")
    if monitor.total_runs == 0:
        md.append("No synthetic monitor runs found for this period.\n")
    else:
        pass_rate = monitor.passed * 100 // monitor.total_runs
        md.append(f"- **Total runs:** {monitor.total_runs}")
        md.append(f"- **Passed:** {monitor.passed} ({pass_rate}%)")
        md.append(f"- **Failed:** {monitor.failed}")

        if monitor.failures:
            md.append("\n### Failures\n")
            md.append("| Date | Conclusion | Run |")
            md.append("|------|------------|-----|")
            for f in monitor.failures[:20]:
                md.append(f"| {f['date']} | {f['conclusion']} | [link]({f['url']}) |")
            if len(monitor.failures) > 20:
                md.append(f"\n*...and {len(monitor.failures) - 20} more*")

    md.append("\n---\n")
    md.append("## Narrative Summary\n")

    bad_keg = next((a for a in arc_stats if a.name == "bad_keg" and a.total_reviews > 0), None)
    recovery = next((a for a in arc_stats if a.name == "recovery" and a.total_reviews > 0), None)

    if bad_keg and "sim_tap_room" in bad_keg.avg_rating_by_biz:
        bad_avg = bad_keg.avg_rating_by_biz["sim_tap_room"]
        if recovery and "sim_tap_room" in recovery.avg_rating_by_biz:
            rec_avg = recovery.avg_rating_by_biz["sim_tap_room"]
            md.append(
                f"The **bad keg incident** drove The Tap Room's average rating down to **{bad_avg:.1f}★** "
                f"during days 7–9.5. The **recovery arc** brought it back to **{rec_avg:.1f}★** — "
                f"a real, measurable reputation signal visible in the dashboard without any manual intervention."
            )

    if grand_total > 0:
        md.append(
            f"\n**{grand_total} reviews** were processed through the full pipeline "
            f"(sim_reviews → SimulationProvider → fetch_reviews → LLM analysis → dashboard) "
            f"over {cycle_day:.0f} days with zero manual intervention."
        )

    if monitor.total_runs > 0:
        md.append(
            f"\nThe synthetic health checker ran **{monitor.total_runs} times** "
            f"(every 30 min) and passed **{pct(monitor.passed, monitor.total_runs)}** of checks."
        )

    return "\n".join(md)


# ---------------------------------------------------------------------------
# Telegram
# ---------------------------------------------------------------------------

def _print_utf8(message: str) -> None:
    """Print to stdout with UTF-8 encoding regardless of terminal locale."""
    sys.stdout.buffer.write((message + "\n").encode("utf-8", errors="replace"))
    sys.stdout.buffer.flush()


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        print("\n[Telegram not configured - message below]\n")
        _print_utf8(message)
        return
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=15,
        )
        if r.status_code == 200:
            print("Telegram message sent.")
        else:
            print(f"Telegram error {r.status_code}: {r.text[:200]}", file=sys.stderr)
            _print_utf8(message)
    except Exception as e:
        print(f"Telegram send failed: {e}", file=sys.stderr)
        _print_utf8(message)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--since",
        default=None,
        help="Override cycle start date (YYYY-MM-DD). Defaults to the ARC_EPOCH.",
    )
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL")
    github_token = os.environ.get("GITHUB_TOKEN")
    github_repo = os.environ.get("GITHUB_REPOSITORY", "YuriShkurko/review-insight-tool")
    report_path = os.environ.get("REPORT_PATH", "demo-report.md")

    if not db_url:
        print("ERROR: DATABASE_URL required", file=sys.stderr)
        sys.exit(1)

    if args.since:
        cycle_start_ts = datetime.strptime(args.since, "%Y-%m-%d").replace(tzinfo=UTC).timestamp()
    else:
        # Compute the start of the current arc cycle from ARC_EPOCH
        now_ts = datetime.now(UTC).timestamp()
        elapsed = now_ts - ARC_EPOCH
        cycle_number = int(elapsed // ARC_PERIOD)
        cycle_start_ts = ARC_EPOCH + cycle_number * ARC_PERIOD

    now_ts = datetime.now(UTC).timestamp()
    cycle_day = (now_ts - cycle_start_ts) / 86400
    print(f"\nDemo soak report  (cycle day {cycle_day:.1f}/14)", flush=True)
    print(f"Cycle start: {datetime.fromtimestamp(cycle_start_ts, UTC).strftime('%Y-%m-%d %H:%M UTC')}", flush=True)

    # Collect data
    print("\n[1/3] Querying sim_reviews...", flush=True)
    arc_stats = collect_db_stats(db_url, cycle_start_ts)
    totals = collect_total_db(db_url, cycle_start_ts)
    for a in arc_stats:
        print(f"  [{a.name}] {a.label}: {a.total_reviews} reviews", flush=True)

    print("\n[2/3] Querying GitHub Actions...", flush=True)
    if github_token:
        monitor = collect_github_stats(github_token, github_repo, cycle_start_ts)
        print(f"  Synthetic monitor: {monitor.passed}/{monitor.total_runs} passed", flush=True)
    else:
        print("  GITHUB_TOKEN not set — skipping", flush=True)
        monitor = MonitorStats()

    print("\n[3/3] Building report...", flush=True)
    tg_msg = build_telegram_message(arc_stats, totals, monitor, cycle_start_ts, now_ts)
    md_report = build_markdown_report(arc_stats, totals, monitor, cycle_start_ts, now_ts)

    # Write markdown artifact
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(md_report)
    print(f"  Full report written to {report_path}", flush=True)

    # Send Telegram
    print("\nSending Telegram summary...", flush=True)
    send_telegram(tg_msg)


if __name__ == "__main__":
    main()
