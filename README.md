# Review Insight Tool

An AI-powered review analysis platform that helps small business owners understand what their customers really think — and what to do about it.

Paste a Google Maps link, fetch reviews, and get tailored insights: top complaints, top praise, action items, risk areas, and a recommended focus — all customized to your business type.

## Table of Contents

- [Why This Exists](#why-this-exists)
- [Features](#features)
- [Quick Start](#quick-start)
- [Screenshots](#screenshots)
- [Usage](#usage)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Review Providers](#review-providers)
- [API](#api)
- [Configuration](#configuration)
- [Project Structure](#project-structure)
- [Development](#development)
- [Development automation](docs/DEVELOPMENT.md)
- [Debug event trail](docs/DEVELOPMENT.md#debug-event-trail)
- [Staging / demo deployment](docs/STAGING.md)
- [Benchmark](#benchmark)
- [Testing](#testing)
- [Specification](#specification)
- [Roadmap](#roadmap)
- [License](#license)

## Why This Exists

Small business owners receive hundreds of reviews but rarely have time to read them all, spot patterns, or turn feedback into action.

Review Insight Tool solves this by:

- **Aggregating reviews** from Google Maps into a single view
- **Surfacing patterns** — what customers love and what frustrates them
- **Generating actionable recommendations** tailored to each business type
- **Saving hours** of manual review reading with AI-powered analysis

## Features

- **Add a business** — paste a Google Maps link and select your business type
- **Fetch reviews** — pull real customer reviews with one click
- **Get AI analysis** — receive a consultant-style assessment with complaints, praise, action items, risk areas, and a recommended focus
- **Business-type-aware insights** — a restaurant gets different analysis than a gym or salon
- **Clean dashboard** — see average rating, review count, and all insights in one view
- **Secure access** — each user sees only their own businesses and data
- **Fresh data** — refreshing reviews replaces the old set and clears stale analysis automatically
- **Competitor comparison (V2)** — link up to 3 competitor businesses, run analysis on them, and generate an AI comparison (strengths, weaknesses, opportunities)
- **Polyglot persistence (V3)** — optional MongoDB layer for comparison caching (4.2x speedup), versioned analysis history, and raw API response archival. Graceful no-op when unconfigured. See [benchmark results](docs/BENCHMARK.md)
- **Production observability (V4)** — OpenTelemetry traces and metrics exported to Grafana Cloud. RED dashboard (request rate, error rate, P95 latency), business metrics (reviews fetched, analyses run, LLM latency/errors, cache hit ratio). Synthetic monitor runs every 30 minutes via GitHub Actions and pings Telegram on failure. Fully no-op when `OTEL_EXPORTER_OTLP_ENDPOINT` is unset.
- **Living demo world (V5)** — persistent demo environment that runs autonomously 24/7. Three businesses with a 14-day narrative arc (craft beer festival → quiet week → bad keg incident → recovery), sine-wave review volume with weekly rhythm, optional LLM-burst reviews for dramatic arc events. Tick worker runs every 30 min via GitHub Actions. End-of-cycle soak report sent to Telegram with human-readable findings.
- **Agent dashboard builder (V7)** — business detail page evolves into a chat-driven command center. The agent can answer natural-language questions, generate chart-ready review trends, preview cards in the chat, and add useful results to a persistent dashboard canvas. Dashboard-building prompts can proactively pin widgets without requiring a separate click. Works with OpenAI or OpenRouter (same SDK, configurable `base_url`). No LLM key needed — mock path remains.
- **Offline demo mode** — bundled dataset of 495 real reviews across 8 businesses for local demos, smoke tests, and CI — no external API keys needed for review fetching

## Quick Start

Requires only [Docker](https://www.docker.com/).

```bash
git clone https://github.com/YuriShkurko/review-insight-tool.git
cd review-insight-tool
cp backend/.env.example backend/.env
make up
make db-upgrade
```

Open http://localhost:3000 and register an account.

> **Default mode (mock):** The app works immediately with generated sample reviews — no API keys needed. To use realistic bundled reviews, switch to [offline demo mode](#offline-demo-mode). To fetch live Google Maps reviews, set `REVIEW_PROVIDER=outscraper` and add your `OUTSCRAPER_API_KEY` and `OPENAI_API_KEY` to `backend/.env`.

<details>
<summary><strong>Quick start with offline demo (recommended for evaluation)</strong></summary>

The fastest way to see the full product with realistic data:

```bash
git clone https://github.com/YuriShkurko/review-insight-tool.git
cd review-insight-tool
cp backend/.env.example backend/.env
# Edit backend/.env: set REVIEW_PROVIDER=offline and add your OPENAI_API_KEY
make up
make db-upgrade
make seed-offline
```

Log in as `demo@example.com` / `demo1234`, then fetch reviews and run analysis for each business.

</details>

<details>
<summary><strong>Local development setup (without Docker Compose)</strong></summary>

Requires Python 3.11+, Node.js 18+, and PostgreSQL 16.

**1. Start PostgreSQL**

Use a local PostgreSQL installation, or start one quickly with Docker:

```bash
docker run --name review-insight-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=review_insight \
  -p 5432:5432 \
  -d postgres:16
```

**2. Backend**

From the repo root. Use the activation line for your OS:

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows (CMD or PowerShell)
# source venv/bin/activate  # macOS / Linux

pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python -m uvicorn app.main:app --reload --port 8000
```

**3. Frontend**

```bash
cd frontend
npm install
cp .env.local.example .env.local
npm run dev
```

Open http://localhost:3000. Backend API docs at http://localhost:8000/docs.

</details>

## Screenshots

1. Login  
   ![Login](docs/screenshots/01-login.png)

2. Business List  
   ![Business List](docs/screenshots/02-business-list.png)

3. Dashboard Header  
   ![Dashboard Header](docs/screenshots/03-dashboard-header.png)

4. Dashboard Insights  
   ![Dashboard Insights](docs/screenshots/04-dashboard-insights.png)

5. Competitors  
   ![Competitors](docs/screenshots/05-competitors.png)

6. Comparison  
   ![Comparison](docs/screenshots/06-comparison.png)

7. Reviews  
   ![Reviews](docs/screenshots/07-reviews.png)

8. Debug Panel Events  
   ![Debug Panel Events](docs/screenshots/08-debug-panel-events.png)

9. Debug Selector Highlight  
   ![Debug Selector Highlight](docs/screenshots/09-debug-selector-highlight.png)

10. Debug Selector Tab  
    ![Debug Selector Tab](docs/screenshots/10-debug-selector-tab.png)

11. Trace ID Header (Network)  
    ![Trace ID Header](docs/screenshots/11-trace-id-network.png)

## Usage

1. **Register** — create an account at `/register`
2. **Add a business** — paste a Google Maps URL, select the business type
3. **Fetch reviews** — click "Fetch Reviews" (header button) to pull customer reviews
4. **Run analysis** — click "Analyze" (header button) to run AI analysis
5. **Chat with the agent** — use the chat command center to ask anything: "What are customers complaining about?", "Graph review volume for the last 3 days", "How do I compare to competitors?"
6. **Build a dashboard** — click "Add to dashboard" on an agent result, or ask the agent to build/customize the dashboard for you. Pinned cards and charts persist in the dashboard canvas across sessions.

> **Tip:** Use **Share → Copy link** from the Google Maps business info panel. Search-bar URLs may not work.

---

## Architecture

```mermaid
graph TB
    U[User] --> F[Frontend Next.js]
    F --> API[Backend FastAPI]

    API --> R[Routes]
    R --> S[Services]
    S --> P[Review Providers: mock / offline / outscraper]
    S --> LLM[OpenAI]
    S --> DB[(PostgreSQL)]
    S --> MDB[(MongoDB - optional)]

    F --> DT[Debug Trail and Selector]
    DT --> UIS[Debug UI Snapshot API]
    UIS --> API

    API --> TM[Trace Middleware and Trace Context]
    TM --> DIP[Debug Dipstick Tools]
    MCP[Cursor MCP Client] --> MCPDBG[review-insight-debug MCP server]
    MCPDBG --> DIP
    DIP --> TM
```

The **Review Provider Layer** separates external review sources from core application logic, so adding a new provider (Yelp, TripAdvisor, etc.) requires only a new provider class and factory registration — no changes to routes, services, or the frontend.

**Backend layers:**

| Layer | Responsibility |
|-------|---------------|
| Routes | HTTP handlers, input validation, auth enforcement |
| Services | Business logic — place resolution, review ingestion, AI analysis, dashboard |
| Providers | Pluggable review source abstraction |
| Mongo | Optional speed layer — comparison cache, analysis history, raw responses |
| Models | SQLAlchemy ORM — User, Business, Review, Analysis |
| Schemas | Pydantic request/response validation |

**Frontend layers:**

| Layer | Responsibility |
|-------|---------------|
| Pages | Next.js App Router pages with client-side data fetching |
| Components | Reusable UI — DashboardView, ReviewList, InsightList; `agent/` tree for chat + dashboard canvas widgets |
| Lib | API client, auth context, TypeScript types, `useAgentChat` SSE hook |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Database | PostgreSQL 16, Alembic migrations, MongoDB (optional — Atlas or local) |
| AI | OpenAI GPT-4o-mini (analysis/comparison) + pluggable agent LLM via provider abstraction (OpenAI or OpenRouter) |
| Auth | JWT (PyJWT), bcrypt |
| Review providers | Mock (built-in), Offline (bundled real reviews), Outscraper (live) |
| Infrastructure | Docker, Docker Compose, AWS ECS Fargate, ECR, ALB, SSM |

## Review Providers

The app uses a pluggable provider architecture for fetching reviews. All providers implement the same `ReviewProvider` interface and return `NormalizedReview` objects, so the rest of the app (analysis, comparison, dashboard) works identically regardless of source.

| Provider | `REVIEW_PROVIDER=` | What it does | API keys needed |
|----------|-------------------|--------------|-----------------|
| **Mock** | `mock` | Generates random reviews seeded by place ID | None |
| **Offline** | `offline` | Loads real review snapshots from `backend/data/offline/` | None (reviews); `OPENAI_API_KEY` for analysis |
| **Outscraper** | `outscraper` | Fetches live Google Maps reviews via Outscraper REST API | `OUTSCRAPER_API_KEY` + `OPENAI_API_KEY` |
| **Simulation** | `simulation` | Reads from `sim_reviews` Postgres table (living demo world). Falls back to Mock for unknown place IDs so CI smoke tests are unaffected. | None (reviews); `OPENAI_API_KEY` for analysis |

Set the provider in `backend/.env` via the `REVIEW_PROVIDER` variable. Default is `mock`.

## API

All endpoints are prefixed with `/api`. Protected endpoints require a `Bearer` token.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | No | Create account |
| `/api/auth/login` | POST | No | Sign in, receive token |
| `/api/auth/me` | GET | Yes | Current user info |
| `/api/businesses` | POST | Yes | Add business |
| `/api/businesses` | GET | Yes | List businesses |
| `/api/businesses/{id}` | GET | Yes | Get business details |
| `/api/businesses/{id}` | DELETE | Yes | Delete business (cascades) |
| `/api/businesses/{id}/fetch-reviews` | POST | Yes | Fetch / replace reviews |
| `/api/businesses/{id}/reviews` | GET | Yes | List reviews |
| `/api/businesses/{id}/analyze` | POST | Yes | Run AI analysis |
| `/api/businesses/{id}/dashboard` | GET | Yes | Dashboard data |
| `/api/businesses/{id}/competitors` | POST | Yes | Link a competitor |
| `/api/businesses/{id}/competitors` | GET | Yes | List linked competitors |
| `/api/businesses/{id}/competitors/{cid}` | DELETE | Yes | Remove a competitor link |
| `/api/businesses/{id}/competitors/comparison` | POST | Yes | Generate AI comparison |
| `/api/businesses/{id}/agent/chat` | POST | Yes | Chat with AI agent (SSE stream) |
| `/api/businesses/{id}/agent/workspace` | GET | Yes | List pinned dashboard widgets |
| `/api/businesses/{id}/agent/workspace` | POST | Yes | Pin a widget directly |
| `/api/businesses/{id}/agent/workspace/{wid}` | DELETE | Yes | Remove a pinned widget |
| `/api/businesses/{id}/agent/conversations` | GET | Yes | List past conversations |

Interactive docs: http://localhost:8000/docs

## Configuration

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/review_insight` |
| `REVIEW_PROVIDER` | Review source: `mock`, `offline`, `outscraper`, or `simulation` | `mock` |
| `OUTSCRAPER_API_KEY` | Outscraper API key (required for real reviews) | — |
| `OUTSCRAPER_REVIEWS_LIMIT` | Max reviews per fetch | `100` |
| `OUTSCRAPER_SORT` | Order: `newest`, `most_relevant`, `highest_rating`, `lowest_rating` | `newest` |
| `OUTSCRAPER_CUTOFF` | Optional Unix timestamp — only reviews newer than this (empty = all). Offset pagination not supported by API. | — |
| `OPENAI_API_KEY` | OpenAI API key (blank = sample analysis) | — |
| `GOOGLE_PLACES_API_KEY` | Google Places API key (blank = extract name from URL) | — |
| `JWT_SECRET_KEY` | Secret for signing tokens | `change-me-in-production` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `1440` |
| `MONGO_URI` | MongoDB connection string (empty = MongoDB features disabled) | — |
| `MONGO_DB_NAME` | MongoDB database name | `review_insight` |
| `COMPARISON_CACHE_TTL_HOURS` | Comparison cache TTL in hours | `24` |
| `RAW_RESPONSE_TTL_DAYS` | Raw API response retention in days | `30` |
| `LLM_PROVIDER` | LLM provider for agent chat: `openai` or `openrouter` | `openai` |
| `LLM_MODEL` | Model for analysis/comparison calls | `gpt-4o-mini` |
| `LLM_AGENT_MODEL` | Model for agent chat calls | `gpt-4o-mini` |
| `OPENROUTER_API_KEY` | OpenRouter API key (if `LLM_PROVIDER=openrouter`) | — |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OTLP collector endpoint (e.g. Grafana Cloud) — empty disables OTEL | — |
| `OTEL_EXPORTER_OTLP_HEADERS` | Auth header for OTLP endpoint (e.g. `Authorization=Basic <token>`) | — |
| `GIT_SHA` | Git commit SHA baked into OTEL service resource attributes | `dev` |
| `DEPLOY_ENV` | Deployment environment tag in OTEL resource attributes | `production` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `http://localhost:8000` |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Pydantic settings
│   │   ├── database.py          # SQLAlchemy engine and session
│   │   ├── mongo.py             # MongoDB client (optional polyglot layer)
│   │   ├── observability.py     # OpenTelemetry init + business metric instruments
│   │   ├── auth.py              # JWT + bcrypt utilities
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Request/response schemas
│   │   ├── routes/              # API route handlers
│   │   ├── services/            # Business logic
│   │   ├── providers/           # Review source providers
│   │   ├── agent/               # Agent executor, tools, system prompt, context window
│   │   ├── llm/                 # LLM provider abstraction (OpenAI / OpenRouter)
│   │   └── mock/                # Sample data generators
│   ├── data/offline/            # Offline demo dataset (JSON)
│   ├── scripts/                 # Utility scripts (seed, etc.)
│   ├── alembic/                 # Database migration scripts
│   ├── alembic.ini              # Alembic configuration
│   ├── tests/                   # pytest suite
│   ├── Dockerfile
│   ├── docker-entrypoint.sh     # Alembic then uvicorn (production / Railway)
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components; agent/ for chat+workspace UI
│   │   └── lib/                 # API client, auth, types, useAgentChat hook
│   ├── Dockerfile               # Local dev (docker-compose)
│   ├── Dockerfile.prod          # Production build for PaaS (e.g. Railway)
│   ├── package.json
│   └── .env.local.example
│
├── docs/
│   ├── screenshots/             # README screenshots
│   ├── BUG_HUNT.md              # Bug hunt test plan
│   ├── BUG_HUNT_LOG.md          # Bug hunt findings log
│   ├── SPEC.md                  # System specification
│   ├── STAGING.md               # Staging / demo deployment notes
│   └── DEVELOPMENT.md           # CI, Makefile automation, debug event trail
│
├── scripts/
│   ├── synthetic_monitor.py     # Full-flow synthetic health check (used by CI)
│   ├── seed_demo.py             # Idempotent demo world seed (businesses + reviews + analysis)
│   ├── tick_demo.py             # Living demo world tick worker (sine wave + arc modulation)
│   └── demo_report.py           # 14-day soak report — DB + GitHub Actions API → Telegram
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # Push/PR: lint, tests, frontend build
│       ├── cd.yml               # Deploy to AWS ECS + post-deploy smoke test
│       ├── synthetic.yml        # Synthetic monitor cron (every 30 min)
│       ├── demo-tick.yml        # Living demo world tick (every 30 min)
│       └── demo-report.yml      # Soak report (weekly + end-of-cycle)
│
├── docker-compose.yml           # Full-stack Docker setup
├── Makefile                     # Developer shortcuts
└── README.md
```

## Development

For a **remote staging/demo** on Railway (PostgreSQL, `PORT`, `CORS_ORIGINS`, build-time `NEXT_PUBLIC_API_URL`, migrate-on-start), see **[docs/STAGING.md](docs/STAGING.md)**.

**CI and local automation** (what runs on GitHub vs `make validate`): **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**.

**Debug event trail** (debug-only floating panel for inspecting API calls, state transitions, and user actions): **[docs/DEVELOPMENT.md#debug-event-trail](docs/DEVELOPMENT.md#debug-event-trail)**.

### Makefile commands

| Command | Description |
|---------|-------------|
| `make up` | Start full stack with Docker Compose |
| `make down` | Stop the stack |
| `make logs` | Follow container logs |
| `make backend` | Start backend locally (no Docker) |
| `make frontend` | Start frontend locally (no Docker) |
| `make dev` | Start both locally (Windows) |
| `make validate` | Same checks as GitHub Actions: `lint` + unit tests + integration tests + `npm run build` (frontend) |
| `make ci-local` | Alias for `make validate` |
| `make test` | Run backend unit tests |
| `make test-integration` | Run backend integration tests (in-memory SQLite) |
| `make test-e2e` | Run E2E tests (requires `make up` and `make db-upgrade`) |
| `make lint` | Run linters (ruff + eslint + prettier checks) |
| `make frontend-build` | `npm run build` in `frontend/` only |
| `make db-upgrade` | Apply Alembic migrations to head (via Docker Compose `exec`) |
| `make db-upgrade-local` | Apply migrations with local `alembic` (`backend/.env` `DATABASE_URL`) |
| `make db-downgrade` | Roll back one migration |
| `make db-current` | Show current Alembic revision |
| `make db-history` | Show migration history |
| `make db-revision` | Autogenerate migration: `make db-revision msg="describe change"` |
| `make db-stamp-head` | Stamp DB at head without running SQL (one-time for legacy DBs) |
| `make db-reset` | Drop all tables + `alembic_version` (escape hatch; then run `make db-upgrade`) |
| `make seed-offline` | Seed offline demo data (Docker Compose `exec` backend) |
| `make seed-offline-local` | Same seed using local Python (`backend/.env` database) |
| `make clean` | Remove build artifacts and caches |

### Database migrations

Schema changes are managed with **Alembic** (not `create_all` at app startup). The **production Docker image** runs `alembic upgrade head` in `docker-entrypoint.sh` before uvicorn (PaaS-friendly). Local **`make up`** still benefits from running **`make db-upgrade`** when you change migrations without rebuilding the image.

**First-time / fresh database**

1. Start Postgres (e.g. `make up`).
2. Apply migrations: `make db-upgrade` (Docker) or `cd backend && alembic upgrade head` (local).

**If `make db-upgrade` fails with `DuplicateTable` / `relation "users" already exists`**

Your Postgres volume still has tables from the old `create_all`-on-startup behavior, but Alembic has never recorded a revision. **Do not** keep re-running `upgrade` — run **once**:

```bash
make db-stamp-head
```

That writes `alembic_version` at `head` without re-creating tables. After that, `make db-upgrade` is a no-op until new migrations ship.

**Typical schema change**

1. Edit SQLAlchemy models under `backend/app/models/`.
2. Generate a revision: `make db-revision msg="add column foo"` (review the generated file under `backend/alembic/versions/`).
3. Apply: `make db-upgrade`.
4. Run tests and smoke the app to confirm existing data still works.

**Existing database from the pre-Alembic era** (tables already match current models, no `alembic_version` table)

Run once so Alembic does not try to recreate tables:

```bash
make db-stamp-head
```

**Escape hatch** (broken or divergent schema): `make db-reset` then `make db-upgrade` (destroys all data).

Integration tests still use `create_all` on an in-memory SQLite database only — production and Docker Postgres always use migrations.

### Offline demo mode

The app ships with a bundled dataset of **495 real reviews** across **8 businesses** so you can run the full product flow — including competitor comparison — without needing an Outscraper API key.

#### Why it exists

- **Demos**: Show the full product to reviewers, friends, or interviewers with realistic data
- **Smoke tests**: Validate the complete fetch → analyze → compare pipeline locally
- **CI**: Push/PR workflows run lint, tests, and frontend build (see [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md))

#### How to enable

```bash
# 1. Start the stack
make up

# 2. Apply database migrations
make db-upgrade

# 3. Set the provider to offline in backend/.env
#    REVIEW_PROVIDER=offline
#    OPENAI_API_KEY=<your key>   ← still needed for AI analysis

# 4. Seed the database with demo businesses and competitor links
make seed-offline

# 5. Log in as demo@example.com / demo1234
# 6. Fetch reviews and run analysis for each business
# 7. Generate a comparison from the business detail page
```

> **Note:** Offline mode provides reviews without an external API, but AI analysis still requires an `OPENAI_API_KEY`. Without one, the app falls back to sample analysis data.

#### What's included

The seed script creates a demo user and populates two scenarios:

| Scenario | Main business | Competitors | Reviews |
|----------|--------------|-------------|---------|
| **Bar** | Lager & Ale (Rothschild, TLV) | Lager & Ale (Ra'anana), Lager & Ale (Herzliya), Beer Garden | 100 + 100 + 100 + 33 |
| **Retail** | Rami Levy (Ariel) | Lala Market | 33 + 33 |

An additional standalone business (Lager & Ale branch, 63 reviews) and Shupersal Deal Ariel (33 reviews) are also seeded.

#### Review providers

| Provider | Reviews source | Needs API key | Best for |
|----------|---------------|---------------|----------|
| `mock` | Random generated reviews | No | Quick dev, unit tests |
| `offline` | Bundled real review snapshots (JSON files) | No (reviews only) | Demos, smoke tests, CI |
| `outscraper` | Live Google Maps reviews | Yes (`OUTSCRAPER_API_KEY`) | Production use |

All three providers produce the same `NormalizedReview` shape, so the rest of the app (analysis, comparison, dashboard) works identically regardless of provider.

#### Extending the dataset

The dataset lives in `backend/data/offline/`. To add a new business:

1. Create a JSON file with reviews (array of `{author, rating, text, published_at}`)
2. Add an entry to `manifest.json` pointing to the file
3. Re-run `make seed-offline`

### Observability

**Structured logs** — all key operations emit `op=<name> duration_ms=<ms> success=<bool>` structured fields. External calls (review providers, LLM) have timeouts and payload limits to fail fast.

**OpenTelemetry (production)** — when `OTEL_EXPORTER_OTLP_ENDPOINT` is set, the backend ships traces, metrics, and auto-instrumented spans to any OTLP-compatible backend (Grafana Cloud, Jaeger, etc.). Fully no-op in local dev when the env var is unset.

| Signal | What's captured |
|--------|----------------|
| Traces | Every HTTP request auto-instrumented via FastAPI + SQLAlchemy + httpx instrumentors |
| `reviews.fetched` | Total reviews fetched per provider call |
| `analyses.run` | Successful AI analysis completions |
| `llm.latency_ms` | End-to-end OpenAI call latency (histogram) |
| `llm.errors` | LLM call failures (timeouts, API errors) |
| `llm.parse_failures` | Responses where OpenAI returned invalid JSON |
| `comparisons.run` | Comparison completions (cache miss path) |
| `comparisons.cache_hits` | MongoDB cache hits (skipped LLM call) |
| `comparisons.cache_misses` | Cache misses (LLM call needed) |

**Synthetic monitor** — `scripts/synthetic_monitor.py` exercises the full user flow (register → create business → fetch → analyze → dashboard → competitor → comparison × 2 → cleanup) and exits non-zero on any failure. Runs every 30 minutes via `.github/workflows/synthetic.yml` and fires a Telegram alert on failure.

To run manually against a live deployment:

```bash
MONITOR_BASE_URL=https://your-backend.example.com python scripts/synthetic_monitor.py
```

**Living demo world** — a persistent demo environment running autonomously on the hosted deployment. Three craft beer bars in Tel Aviv evolve over time via a three-layer modulation system:

| Layer | What it does |
|-------|-------------|
| Sine wave | Daily volume rhythm with phase offsets — bars peak at different times |
| Weekly schedule | Friday night rush (2.8×), Sunday Beer Garden brunch (3.2×), Thursday buildup, Monday dip |
| 14-day narrative arc | Festival weekend → quiet week → bad keg incident at Tap Room (rating crashes) → recovery arc → wind-down → repeat |

The tick worker (`demo-tick.yml`) injects new reviews every 30 minutes and calls fetch-reviews + analyze. For arc "burst" moments, reviews are generated via `gpt-4o-mini` if `OPENAI_API_KEY` is set; otherwise falls back to the hand-authored template bank.

A soak report runs weekly and at end-of-cycle, querying the DB and GitHub Actions history to produce a human-readable Telegram summary of what the story arc produced and how the system held up.

Demo login (hosted):
- **URL:** the ALB public DNS (see GitHub → Settings → Variables → `BACKEND_PUBLIC_URL`)
- **Email:** `demo@review-insight.app`
- **Password:** `DemoWorld2026!`

To seed or re-seed the demo world manually:

```bash
DATABASE_URL=... DEMO_API_URL=http://... python scripts/seed_demo.py
```

To run a tick manually:

```bash
DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py --dry-run
DATABASE_URL=... DEMO_API_URL=http://... python scripts/tick_demo.py --show-arc
```

### Database reset (escape hatch)

If the database is corrupted or out of sync with migrations, drop everything and reapply:

```bash
make db-reset
make db-upgrade
```

Then re-seed if needed (`make seed-offline`) and re-register users.

## Benchmark

The polyglot persistence layer was benchmarked on AWS ECS Fargate (Postgres-only vs Postgres + MongoDB Atlas M0).

| Operation | Postgres-only | + MongoDB | Change |
|-----------|--------------|-----------|--------|
| Comparison (cold) | 5,797 ms | 5,190 ms | same (LLM-bound) |
| Comparison (cache hit) | 5,049 ms | 1,235 ms | **4.2x faster** |
| Analysis history query | N/A | 575 ms | **new capability** |

```
Comparison latency (ms) — lower is better

Postgres-only (every call hits LLM):
  cold     |████████████████████████████████████████████████████| 5,797 ms
  "cached" |████████████████████████████████████████████████    | 5,049 ms

Postgres + MongoDB (cache hit skips LLM):
  cold     |████████████████████████████████████████████████    | 5,190 ms
  cached   |██████████                                         | 1,235 ms  ← 4.2x faster
```

Cache hits skip the OpenAI LLM call entirely and serve a MongoDB document instead. All MongoDB features gracefully no-op when `MONGO_URI` is unset.

Full results: [docs/BENCHMARK.md](docs/BENCHMARK.md)

```bash
make benchmark   # run against a live backend
```

## Testing

Backend tests use **pytest**:

```bash
make test                # unit tests (no server required)
make test-integration    # integration tests (in-memory SQLite, no server required)
make test-e2e            # end-to-end tests (requires running backend via make up)
```

### Continuous integration

On every push and pull request to `main` / `master`, **GitHub Actions** runs backend lint (`ruff`), backend tests (unit + integration), and frontend lint + production build. E2E tests are not run in CI (they need a live server). Details: **[docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)**.

After every deployment, the **synthetic monitor** (`synthetic.yml`) automatically runs the full user-flow check against the live backend. It also runs on a 30-minute cron schedule. Results are uploaded as workflow artifacts. Configure `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` in GitHub repo secrets to receive phone alerts on failure.

To match CI locally before you push:

```bash
make validate
```

### Unit tests

| Area | Coverage |
|------|----------|
| Provider normalization | Mock data shape, determinism, field validation, source tagging |
| Analysis normalization | Insight coercion, string normalization, missing-field defaults |
| Prompt generation | Business-type-specific prompts for all 8 types + generic fallback |
| Schema validation | Dashboard response shape, analysis fields, business type enum |
| URL parsing | Google Maps URL formats, short-link resolution, place ID extraction |

### Integration tests

Backend integration tests (`tests/integration/`) use an in-memory SQLite database and mock providers to test multi-layer flows without external dependencies:

- Full business + review + analysis lifecycle
- Refresh clears stale analysis
- Competitor link flow and duplicate/self-link protections
- Competitor promotion (competitor-only → regular business)

### End-to-end test

A single E2E test (`tests/e2e/test_full_flow.py`) verifies the full core workflow against a running backend:

1. Register a user
2. Create a business
3. Fetch reviews
4. Run analysis
5. Validate dashboard contains all expected fields
6. Verify that refreshing reviews clears stale analysis

## Specification

For detailed system behavior, user flows, analysis output shapes, and known limitations, see [docs/SPEC.md](docs/SPEC.md).

## Roadmap

- [x] Competitor comparison — side-by-side insights against linked competitor businesses
- [ ] Additional review providers — Yelp, TripAdvisor, App Store, Play Store
- [x] Database migrations — Alembic for safe schema evolution
- [x] Delete businesses
- [x] Offline demo dataset
- [ ] Secure auth — refresh tokens, httpOnly cookies
- [ ] Background jobs — Celery/Redis for async review fetching
- [ ] Export reports — PDF/CSV
- [x] CI/CD pipeline — GitHub Actions CI (lint + tests + build) + CD (ECS deploy) + synthetic monitor (every 30 min)
- [x] Living demo world — autonomous 14-day narrative arc, sine-wave + weekly modulation, LLM burst reviews, soak report
- [x] Agent dashboard builder — chat command center with tool calls, SSE streaming, chart-ready trends, and persistent dashboard canvas widgets

## License

Personal portfolio project. Not licensed for commercial use.
