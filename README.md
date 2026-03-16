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
- **Offline demo mode** — bundled dataset of 595 real reviews across 9 businesses for local demos, smoke tests, and CI — no external API keys needed for review fetching

## Quick Start

Requires only [Docker](https://www.docker.com/).

```bash
git clone https://github.com/YuriShkurko/review-insight-tool.git
cd review-insight-tool
cp backend/.env.example backend/.env
make up
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

| Login | Business List |
|-------|--------------|
| ![Login](docs/screenshots/01-login.png) | ![Business List](docs/screenshots/02-business-list.png) |

| Dashboard — Header & Stats | Dashboard — Insights |
|----------------------------|---------------------|
| ![Dashboard Header](docs/screenshots/03-dashboard-header.png) | ![Dashboard Insights](docs/screenshots/04-dashboard-insights.png) |

| Competitors | Comparison |
|-------------|------------|
| ![Competitors](docs/screenshots/05-competitors.png) | ![Comparison](docs/screenshots/06-comparison.png) |

| Reviews |
|---------|
| ![Reviews](docs/screenshots/07-reviews.png) |

## Usage

1. **Register** — create an account at `/register`
2. **Add a business** — paste a Google Maps URL, select the business type
3. **Fetch reviews** — click "Fetch Reviews" to pull customer reviews
4. **Run analysis** — click "Run Analysis" to generate tailored insights
5. **View dashboard** — see your rating, AI summary, complaints, praise, action items, and risk areas
6. **Compare with competitors (optional)** — on a business page, add up to 3 competitors (Google Maps URLs), fetch and analyze each, then click "Generate Comparison" for AI-generated strengths, weaknesses, and opportunities

> **Tip:** Use **Share → Copy link** from the Google Maps business info panel. Search-bar URLs may not work.

---

## Architecture

```mermaid
graph TB
    User([User]) --> Frontend

    subgraph Client
        Frontend["Next.js Frontend<br/>React · TypeScript · Tailwind"]
    end

    subgraph Server
        API["FastAPI Backend<br/>Routes · Services · Auth"]
    end

    subgraph Providers
        RP["Review Provider Layer<br/>Outscraper · Offline · Mock"]
    end

    subgraph External
        LLM["LLM Engine External<br/>OpenAI GPT-4o-mini"]
    end

    subgraph Data
        DB[("PostgreSQL<br/>Users · Businesses<br/>Reviews · Analyses")]
    end

    Frontend -- "HTTP / JSON" --> API
    API --> RP
    API --> LLM
    API --> DB
```

The **Review Provider Layer** separates external review sources from core application logic, so adding a new provider (Yelp, TripAdvisor, etc.) requires only a new provider class and factory registration — no changes to routes, services, or the frontend.

**Backend layers:**

| Layer | Responsibility |
|-------|---------------|
| Routes | HTTP handlers, input validation, auth enforcement |
| Services | Business logic — place resolution, review ingestion, AI analysis, dashboard |
| Providers | Pluggable review source abstraction |
| Models | SQLAlchemy ORM — User, Business, Review, Analysis |
| Schemas | Pydantic request/response validation |

**Frontend layers:**

| Layer | Responsibility |
|-------|---------------|
| Pages | Next.js App Router pages with client-side data fetching |
| Components | Reusable UI — DashboardView, ReviewList, InsightList |
| Lib | API client, auth context, TypeScript types |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Database | PostgreSQL 16 |
| AI | OpenAI GPT-4o-mini |
| Auth | JWT (PyJWT), bcrypt |
| Review providers | Mock (built-in), Offline (bundled real reviews), Outscraper (live) |
| Infrastructure | Docker, Docker Compose |

## Review Providers

The app uses a pluggable provider architecture for fetching reviews. All providers implement the same `ReviewProvider` interface and return `NormalizedReview` objects, so the rest of the app (analysis, comparison, dashboard) works identically regardless of source.

| Provider | `REVIEW_PROVIDER=` | What it does | API keys needed |
|----------|-------------------|--------------|-----------------|
| **Mock** | `mock` | Generates random reviews seeded by place ID | None |
| **Offline** | `offline` | Loads real review snapshots from `backend/data/offline/` | None (reviews); `OPENAI_API_KEY` for analysis |
| **Outscraper** | `outscraper` | Fetches live Google Maps reviews via Outscraper REST API | `OUTSCRAPER_API_KEY` + `OPENAI_API_KEY` |

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

Interactive docs: http://localhost:8000/docs

## Configuration

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/review_insight` |
| `REVIEW_PROVIDER` | Review source: `mock`, `offline`, or `outscraper` | `mock` |
| `OUTSCRAPER_API_KEY` | Outscraper API key (required for real reviews) | — |
| `OUTSCRAPER_REVIEWS_LIMIT` | Max reviews per fetch | `100` |
| `OUTSCRAPER_SORT` | Order: `newest`, `most_relevant`, `highest_rating`, `lowest_rating` | `newest` |
| `OUTSCRAPER_CUTOFF` | Optional Unix timestamp — only reviews newer than this (empty = all). Offset pagination not supported by API. | — |
| `OPENAI_API_KEY` | OpenAI API key (blank = sample analysis) | — |
| `GOOGLE_PLACES_API_KEY` | Google Places API key (blank = extract name from URL) | — |
| `JWT_SECRET_KEY` | Secret for signing tokens | `change-me-in-production` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `1440` |

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
│   │   ├── auth.py              # JWT + bcrypt utilities
│   │   ├── models/              # ORM models
│   │   ├── schemas/             # Request/response schemas
│   │   ├── routes/              # API route handlers
│   │   ├── services/            # Business logic
│   │   ├── providers/           # Review source providers
│   │   └── mock/                # Sample data generators
│   ├── data/offline/            # Offline demo dataset (JSON)
│   ├── scripts/                 # Utility scripts (seed, etc.)
│   ├── tests/                   # pytest suite
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js pages
│   │   ├── components/          # React components
│   │   └── lib/                 # API client, auth, types
│   ├── Dockerfile
│   ├── package.json
│   └── .env.local.example
│
├── docs/
│   ├── screenshots/             # README screenshots
│   ├── BUG_HUNT.md              # Bug hunt test plan
│   ├── BUG_HUNT_LOG.md          # Bug hunt findings log
│   └── SPEC.md                  # System specification
│
├── docker-compose.yml           # Full-stack Docker setup
├── Makefile                     # Developer shortcuts
└── README.md
```

## Development

### Makefile commands

| Command | Description |
|---------|-------------|
| `make up` | Start full stack with Docker Compose |
| `make down` | Stop the stack |
| `make logs` | Follow container logs |
| `make backend` | Start backend locally (no Docker) |
| `make frontend` | Start frontend locally (no Docker) |
| `make dev` | Start both locally (Windows) |
| `make test` | Run backend unit tests |
| `make test-integration` | Run backend integration tests (in-memory SQLite) |
| `make test-e2e` | Run E2E tests (requires `make up`) |
| `make lint` | Run linters |
| `make db-reset` | Drop all tables (backend recreates on restart) |
| `make seed-offline` | Seed database with offline demo businesses |
| `make clean` | Remove build artifacts and caches |

### Offline demo mode

The app ships with a bundled dataset of **595 real reviews** across **9 businesses** so you can run the full product flow — including competitor comparison — without needing an Outscraper API key.

#### Why it exists

- **Demos**: Show the full product to reviewers, friends, or interviewers with realistic data
- **Smoke tests**: Validate the complete fetch → analyze → compare pipeline locally
- **Future CI**: Deterministic dataset with no external dependencies for automated testing

#### How to enable

```bash
# 1. Start the stack
make up

# 2. Set the provider to offline in backend/.env
#    REVIEW_PROVIDER=offline
#    OPENAI_API_KEY=<your key>   ← still needed for AI analysis

# 3. Seed the database with demo businesses and competitor links
make seed-offline

# 4. Log in as demo@example.com / demo1234
# 5. Fetch reviews and run analysis for each business
# 6. Generate a comparison from the business detail page
```

> **Note:** Offline mode provides reviews without an external API, but AI analysis still requires an `OPENAI_API_KEY`. Without one, the app falls back to sample analysis data.

#### What's included

The seed script creates a demo user and populates two scenarios:

| Scenario | Main business | Competitors | Reviews |
|----------|--------------|-------------|---------|
| **Bar** | Lager & Ale (Rothschild, TLV) | Lager & Ale (Ra'anana), Lager & Ale (Herzliya), Beer Garden | 100 + 100 + 100 + 33 |
| **Retail** | Rami Levy (Ariel) | Abu Ali Supermarket, Lala Market | 33 + 33 + 33 |

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

The backend logs all key operations with structured fields:

- **Auth**: registration, login (success/failure)
- **Business**: creation with timing
- **Reviews**: provider fetch duration, review count, payload truncation
- **Analysis**: LLM call duration, review count, parse failures
- **Dashboard**: aggregation timing

Logs use `op=<name> duration_ms=<ms> success=<bool>` format for easy searching and monitoring. External calls (review providers, LLM) have timeouts and payload limits to fail fast instead of hanging.

### Database reset

The project uses `create_all` (no Alembic). Schema changes require dropping tables. **V2 adds the `competitor_links` table and `businesses.is_competitor` column** — if you upgrade from a pre-V2 database, run a reset so the schema is recreated:

```bash
make db-reset
# Then restart the backend
```

## Testing

Backend tests use **pytest**:

```bash
make test                # unit tests (no server required)
make test-integration    # integration tests (in-memory SQLite, no server required)
make test-e2e            # end-to-end tests (requires running backend via make up)
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
- [ ] Database migrations — Alembic for safe schema evolution
- [x] Delete businesses
- [x] Offline demo dataset
- [ ] Secure auth — refresh tokens, httpOnly cookies
- [ ] Background jobs — Celery/Redis for async review fetching
- [ ] Export reports — PDF/CSV
- [ ] CI/CD pipeline

## License

Personal portfolio project. Not licensed for commercial use.
