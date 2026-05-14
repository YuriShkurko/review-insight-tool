# Business Insight — Live Demo Run (Engineering Case Study)

A ~14-day live soak of the **Business Insight** app, exercised continuously
by synthetic monitoring and a scripted "demo world" worker, with Telegram
alerting on failure. One real upstream incident landed during the run and
was caught by the alerting path; that case is documented honestly below.

> **Sourcing conventions used in this report**
> - **[Repo]** — fact verified against committed code/workflows/artifacts.
> - **[Owner]** — owner-provided context, not independently verified here.
> - **[Unverified]** — needs follow-up; consolidated in [§ Remaining verification](#remaining-verification).
> - No metrics, run IDs, dates, or uptime figures have been invented.
> - Sensitive values are redacted with explicit placeholders.

## Summary

| | |
|---|---|
| **Cycle window** | Apr 24 – May 8, 2026 (14 days). **[Repo]** Anchored to `ARC_EPOCH = 1776988800` in `scripts/tick_demo.py` and to the archived report `demo-report-final-2026-05-08.md`. |
| **App under test** | Business Insight — FastAPI + Next.js + PostgreSQL, plus an optional MongoDB comparison cache. |
| **Where it ran** | Compute on **AWS ECS Fargate** (backend + frontend behind an ALB). Database on **Railway** managed Postgres. **[Repo + Owner]** |
| **What exercised it** | A 12-step synthetic monitor on the user-flow path, plus a scripted "demo world" tick worker injecting reviews into a 14-day narrative arc. Both on GitHub Actions cron. **[Repo]** |
| **Alerting** | Telegram bot from `scripts/synthetic_monitor.py` and `scripts/demo_report.py`. **[Repo]** |
| **Headline numbers (per archived report)** | 1,971 reviews injected; 199 / 221 synthetic runs passed (≈90%). **[Repo: `demo-report-final-2026-05-08.md`]** |
| **Notable real-world event** | Telegram alert for a login/database failure during a Railway provider issue on **May 6, ~12:42 PM Israel time** (≈09:42 UTC). **[Owner]** |
| **End of soak** | Archive commit `a44544f` "Archive living demo soak and disable schedules", Sun May 10 07:09 IDT, switched all three cron workflows to `workflow_dispatch`-only. **[Repo]** |

## System Under Test

| Component | Where | Evidence |
|---|---|---|
| FastAPI backend | AWS ECS Fargate (`review-insight-backend`, eu-central-1) | `.github/workflows/cd.yml`, `infrastructure/README.md` **[Repo]** |
| Next.js frontend | AWS ECS Fargate (`review-insight-frontend`) | `cd.yml`, `infrastructure/05-ecs.sh` **[Repo]** |
| Load balancer | AWS ALB (`review-insight-alb`), HTTP or HTTPS depending on cert state | `infrastructure/04-alb.sh`, `cd.yml` "Print public URL" step **[Repo]** |
| Database | **Railway** managed PostgreSQL | `docs/STAGING.md` Railway path **[Repo]** + Owner |
| Comparison cache | Optional MongoDB Atlas | `docs/OBSERVABILITY_PLAN.md` architecture diagram **[Repo]** |
| CI / CD | GitHub Actions | `.github/workflows/{ci,cd}.yml` **[Repo]** |
| Observability hooks | OpenTelemetry → Grafana Cloud (planned/wired) | `docs/OBSERVABILITY_PLAN.md`, `infrastructure/grafana/dashboards/{red,business-metrics}.json` **[Repo]** |

The live app used the `simulation` review provider: rows in a `sim_reviews`
Postgres table were written by the tick worker, then read back through the
normal `SimulationProvider` → `fetch_reviews` → analyze → dashboard path. The
synthetic data therefore traversed the same code an external user's reviews
would.

## Operational Pipeline

### Synthetic monitor — `scripts/synthetic_monitor.py` + `.github/workflows/synthetic.yml`

Per run, the monitor executes the full user journey end-to-end, with
dependency-aware skipping so an upstream failure doesn't manufacture
downstream "failures":

1. `GET /api/health`
2. `POST /api/auth/register` (one-off `bot-<uuid>@synthetic-monitor.com`)
3. `POST /api/businesses` (sandbox `place_id`)
4. `POST /api/businesses/{id}/fetch-reviews`
5. `POST /api/businesses/{id}/analyze`
6. `GET /api/businesses/{id}/dashboard` + assertion that `ai_summary` is present
7. `POST .../competitors` (link a competitor)
8–9. fetch + analyze the competitor
10. `POST .../competitors/comparison` (cold — LLM)
11. `POST .../competitors/comparison` (warm — expects Mongo cache hit)
12. `DELETE /api/businesses/{id}` (cleanup, runs even on failure)

**Schedule:** `cron: */30 * * * *` (every 30 minutes), plus a `workflow_call`
triggered after every successful CD deploy. **[Repo]** Confirmed via
`git show a44544f^:.github/workflows/synthetic.yml`. The archive commit on
May 10 disabled the cron and left `workflow_dispatch` + `workflow_call` only.

### Demo "world tick" — `scripts/tick_demo.py` + `.github/workflows/demo-tick.yml`

A three-layer director that gives the dashboard real, narrative motion
rather than random noise:

- **Layer 1** — per-business sine wave (daily rhythm, phase-offset per bar).
- **Layer 2** — weekly schedule (Fri/Sat rush, Sunday brunch, midweek happy hour, Monday dip).
- **Layer 3** — a 14-day narrative arc anchored to `ARC_EPOCH = 2026-04-24 00:00 UTC`: `festival_weekend` → `quiet_week` → `bad_keg` → `recovery` → `pre_cycle_wind_down`.

Each tick computes `n_reviews` per place from the layered modulation, then:
inserts into `sim_reviews` (idempotent on `(place_id, external_id)`), and
calls the app's own `fetch-reviews` + `analyze` endpoints. Burst arcs
optionally generate up to two LLM-written reviews per business via
`OPENAI_API_KEY`, with a hand-authored template bank as fallback.

**Schedule (workflow file):** `cron: */30 * * * *` (every 30 minutes). **[Repo]**
**Observed cadence:** the owner recalls dashboard movement appearing
"roughly every couple of hours" **[Owner]**. This is consistent with the
script's quiet-tick behaviour — during the `quiet_week` and `wind_down`
arcs, many 30-minute slots compute `n_reviews == 0` and the tick prints
`"quiet tick, skipping"` without inserting anything. The cron itself
fires every 30 minutes; what reaches the dashboard is bursty by design.

### Soak report — `scripts/demo_report.py` + `.github/workflows/demo-report.yml`

Pulls per-arc stats from Postgres and synthetic-monitor pass/fail history
from the GitHub Actions API, then writes a Markdown artifact and sends a
Telegram roll-up. **Schedule:** weekly Mondays at 09:00 UTC plus
cycle-boundary firings at May 8 / May 22 / Jun 5, 02:00 UTC. **[Repo]**

### Failure → alert path

Both `synthetic_monitor.py` and `demo_report.py` POST to the Telegram Bot
API. The synthetic monitor sends **critical** alerts the moment a load-bearing
step fails (health, registration, business creation) and a consolidated
end-of-run alert for any other failures. Token + chat ID come from GitHub
Actions secrets and are redacted throughout this document.

## Soak Results

From the committed `demo-report-final-2026-05-08.md`, generated 2026-05-10
03:57 UTC, covering Apr 24 – May 8: **[Repo]**

| Arc phase | Dates | Reviews | Tap Room avg | Notes |
|---|---|---|---|---|
| 🎪 Craft Beer Festival | Apr 24 – Apr 26 | 802 | 4.5★ | Burst, high volume across all three bars |
| 😴 Quiet Week | Apr 26 – May 01 | 283 | 4.3★ | Baseline / quiet-tick phase |
| 💀 Bad Keg Incident | May 01 – May 03 | 554 | **3.2★** | Deliberate reputation dip — visible in dashboard |
| 💚 Recovery Arc | May 03 – May 06 | 213 | **4.7★** | Recovery signal — visible in dashboard |
| 🌅 Wind-Down | May 06 – May 08 | 119 | 4.1★ | Cycle close |
| **Total** | **14 days** | **1,971** | — | — |

Synthetic monitor history over the same window (from the same archived
report's footer): **199 / 221 runs passed (≈90%), 22 failed or cancelled.**
No date-level breakdown of those 22 failures is recorded in the archive.

The "bad keg → recovery" swing (3.2★ → 4.7★ on The Tap Room) is the cleanest
demonstration that the pipeline ran end-to-end without human intervention:
a deliberately injected reputation signal made it through `sim_reviews` →
`SimulationProvider` → `fetch_reviews` → analysis → dashboard.

## Incident: May 6 Telegram Alert

### What happened **[Owner]**

> At **12:42 PM on May 6, 2026, Israel time** (UTC+3 → ~09:42 UTC), the
> owner received a Telegram alert indicating a **login / database-related
> failure**. The database was hosted on **Railway**, and Railway was having
> issues around the same time. The synthetic monitor + alerting path
> therefore detected a real upstream availability problem during the live
> demo run.

Year (2026) is independently anchored by `ARC_EPOCH = 1776988800` and by
the archive commit dated 2026-05-10. **[Repo]**

### How the code would have fired that alert **[Repo]**

Given the failure description and the synthetic monitor source:

- A login/DB outage on Railway-hosted Postgres breaks `POST /api/auth/register`, which persists a user row.
- `check_register()` short-circuits the rest of the run and sends `"CRITICAL: Registration failed — auth or DB may be broken"` via Telegram (`scripts/synthetic_monitor.py:292`).
- If `/api/health` itself touched the failing DB and went down first, the message would have been `"CRITICAL: Health check failed — backend may be down"` (`scripts/synthetic_monitor.py:288`).

In both cases, the alert names *where* the system broke (auth/DB vs LLM vs
dashboard composition), not just *that* it broke — which is the point of
running a journey monitor instead of a `/health` poller.

### What is and isn't verified

- **Verified** that the alert path, message strings, 30-minute cadence, and Railway-as-database choice all match the owner's report. **[Repo + Owner]**
- **Not verified** here: the exact GitHub Actions run ID, the run's failed step, the Telegram message payload as actually delivered, and Railway's status-page state at ~09:42 UTC on May 6, 2026. The `gh` CLI is not available in this environment. **[Unverified]** — see [§ Remaining verification](#remaining-verification).

### What the incident demonstrates

- A real upstream dependency (Railway-managed Postgres) degraded.
- A journey-style synthetic monitor on a 30-minute cron caught it without depending on a user noticing.
- The Telegram channel delivered an actionable, classifiable alert to the owner's phone within the next-check window — the "phone-pageable" loop described in `docs/OBSERVABILITY_PLAN.md`, exercised by a real incident rather than a drill.

## Validation and Reliability Signals

| Signal | Source |
|---|---|
| Backend lint | Ruff `check` + `format --check` in CI (`ci.yml` → backend job) |
| Backend unit + integration | Pytest, with in-memory SQLite for integration (`ci.yml`) |
| Frontend lint + build | ESLint + Prettier + `next build` (`ci.yml`) |
| Browser E2E | Playwright job in `ci.yml` (postgres:16 service, scripted LLM provider) |
| Pre-deploy guard | `ci-check` job in `cd.yml` (ruff + tsc) must pass before image build |
| Post-deploy smoke | `cd.yml` calls `synthetic.yml` after `wait-for-service-stability: true` |
| Continuous availability | `synthetic.yml` cron `*/30 * * * *` (during soak) hitting the 12-step user flow |
| Continuous data motion | `demo-tick.yml` cron `*/30 * * * *` injecting + re-analyzing |
| Weekly / cycle summary | `demo-report.yml` — Mondays 09:00 UTC plus May 8 / May 22 / Jun 5 |
| Aggregate failure window | 22 failed/cancelled out of 221 synthetic runs (≈90% pass rate) per archived footer |
| Real failure caught | May 6 ~09:42 UTC login/DB alert during Railway issue **[Owner, code-path consistent]** |

## What Worked Well

- **Journey-style monitoring beat health-check pings.** The synthetic
  monitor exercised register → create → fetch → analyze → dashboard →
  compare (cold + warm) → cleanup. When it failed, the failure named the
  station, not just the line.
- **Dependency-aware skipping kept the signal clean.** When `fetch_reviews`
  failed, `analyze` and `dashboard` were recorded as `skipped: blocked` rather
  than counted as independent failures (`STEP_DEPENDENCIES` in the script).
- **Telegram surfaced a real outage**, not just synthetic test noise (the
  May 6 event).
- **Two infrastructure paths were exercised.** Compute on AWS ECS Fargate
  through `cd.yml` + `infrastructure/05-ecs.sh`; database on Railway through
  the `docs/STAGING.md` path. Real infra, both sides.
- **Narrative content paid off as a product test.** The 3.2★ → 4.7★ swing on
  The Tap Room during the bad-keg → recovery arcs is a clean
  end-to-end demonstration that the analysis + dashboard surface a real
  reputation signal.
- **Cost control was explicit.** `make aws-teardown`, the archive commit's
  disabling of all three cron schedules, and the in-YAML comment
  *"Schedule disabled after AWS teardown to avoid recurring Actions runs"*
  show the soak was wound down deliberately.

## Gaps / What I Would Improve

- **No structured incident timeline.** A short per-incident post-mortem
  (timestamp, what fired, upstream root cause, time-to-ack, time-to-green)
  would beat any one Telegram message.
- **No formal SLO.** "199 / 221 = 90%" is a coarse roll-up. Some of those
  22 failures were likely flaky LLM calls or test-data issues rather than
  availability problems; classifying them by step (`check_health` vs
  `check_analyze` vs `check_comparison`) would give a real availability number.
- **No runbook for the May-6 class of failure.** A one-pager — *"Telegram
  CRITICAL: auth/DB → check Railway status, then …"* — would close the loop
  the next time it fires.
- **Limited evidence retention.** The synthetic monitor's per-run artifact
  retention is 7 days; the soak-report artifact is 90 days. Capturing the
  May 6 run details before they expire is a one-shot.
- **No saved screenshots / message exports in this report.** The dashboard
  during `bad_keg` vs `recovery`, plus the May 6 Telegram alert itself,
  would carry the story better than prose.

## Portfolio / CV Summary

- **Ran a real 14-day production-style soak.** Business Insight ran on AWS
  ECS Fargate + Railway Postgres from Apr 24 – May 8 2026, continuously
  exercised by a 12-step synthetic user-journey monitor on a 30-minute
  cron and a scripted "demo world" worker that injected a 14-day narrative
  arc of reviews into a real DB.
- **Detected a real upstream incident.** On May 6, 12:42 PM IDT
  (≈09:42 UTC), the synthetic monitor's auth/DB step failed during a
  Railway provider issue and fanned out a classified Telegram alert — the
  monitoring path caught a real dependency problem, not just synthetic
  bugs.
- **Operated with engineering discipline.** Journey-style monitoring with
  dependency-aware skipping, CI gating before deploy, post-deploy smoke,
  weekly soak reports pulling pass/fail history from the GitHub Actions
  API, and an explicit, in-repo teardown step (`make aws-teardown` +
  workflow archive commit) once the run was over.

## Remaining Verification

The items below need someone with `gh` CLI access, the Telegram archive,
or the Railway status archive to close out. They are intentionally listed
together rather than scattered through the report.

1. **Per-run links for the synthetic monitor over Apr 24 – May 8.** Run
   `gh run list --workflow synthetic.yml --created 2026-04-24..2026-05-08 --limit 300`
   and paste a trimmed table of failures.
2. **The May 6 incident's specific run.** Run
   `gh run list --workflow synthetic.yml --created 2026-05-06 --limit 50`,
   then `gh run view <RUN_ID> --log` to confirm which step failed
   (`check_health` vs `check_register`), the alert payload string, and the
   recovery run that next went green.
3. **Railway status archive for ~09:42 UTC on 2026-05-06.** Confirm the
   provider-side outage independently.
4. **Telegram message archive.** Save the actual alert + the soak-report
   roll-ups; they're better evidence than the script source quoted here.
5. **Demo-tick cadence reconciliation.** The workflow file says
   `*/30 * * * *`; the owner recalls dashboard movement closer to
   every couple of hours. Likely explained by the script's quiet-tick
   skipping during low-volume arcs, but worth confirming against the
   `sim_reviews` insert timestamps in the archived CSV.
6. **Archive CSV location.** The commit `a44544f` added
   `infrastructure/living-demo-world-sim-reviews-2026-05-08.csv` (1,972
   rows in its diff), but the file is not in the current working tree.
   Confirm whether it was intentionally moved/removed in a later commit.
7. **Failure classification for the "22 failed/cancelled" runs.** Split
   into real availability failures vs flaky-step failures to derive a
   defensible availability number.

## Redactions Applied

All values below are replaced with explicit placeholders in any markdown
the demo run touches:

- Public demo URL (ALB DNS) → `<redacted-public-demo-url>`
- Demo login email → `<redacted-demo-login>`
- Demo password → `<redacted-demo-password>`
- Telegram bot token, Telegram chat ID, `DATABASE_URL`, AWS account ID,
  AWS access key / secret, OpenAI key — never pasted in this report.

The archive `demo-report-final-2026-05-08.md` and the working
`demo-report.md` were already redacted in an earlier pass (the previously
verbatim ALB DNS and the demo login string are now placeholders).

**Note on source constants.** `scripts/tick_demo.py`, `scripts/demo_report.py`,
and `scripts/seed_demo.py` read demo credentials from `DEMO_EMAIL` /
`DEMO_PASSWORD` env vars, with safe placeholder defaults
(`demo@example.local` / `local-demo-password`) for local development. Real
demo credentials should be provided via the deploy environment (Railway
Variables / GitHub Actions secrets), never committed.
