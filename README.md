# Review Insight Tool

An AI-powered review analysis platform that helps small business owners understand what their customers really think — and what to do about it.

Paste a Google Maps link, fetch reviews, and get tailored insights: top complaints, top praise, action items, risk areas, and a recommended focus — all customized to your business type.

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

## Quick Start

Requires only [Docker](https://www.docker.com/).

```bash
git clone https://github.com/YOUR_USERNAME/review-insight-tool.git
cd review-insight-tool
cp backend/.env.example backend/.env
make up
```

Open http://localhost:3000 and register an account.

> The app works immediately with sample data. To use real reviews and AI analysis, add your `OUTSCRAPER_API_KEY` and `OPENAI_API_KEY` to `backend/.env` and restart.

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

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
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

| Login | Add Business | Dashboard |
|-------|-------------|-----------|
| ![Login](docs/screenshots/01-login.png) | ![Add Business](docs/screenshots/02-add-business.png) | ![Dashboard](docs/screenshots/03-dashboard.png) |

| Insights & Actions | Reviews |
|--------------------|---------|
| ![Insights](docs/screenshots/04-insights.png) | ![Reviews](docs/screenshots/05-reviews.png) |

## Usage

1. **Register** — create an account at `/register`
2. **Add a business** — paste a Google Maps URL, select the business type
3. **Fetch reviews** — click "Fetch Reviews" to pull customer reviews
4. **Run analysis** — click "Run Analysis" to generate tailored insights
5. **View dashboard** — see your rating, AI summary, complaints, praise, action items, and risk areas

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
        RP["Review Provider Layer<br/>Outscraper · Sample Data"]
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
| Review providers | Sample data (built-in), Outscraper |
| Infrastructure | Docker, Docker Compose |

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
| `/api/businesses/{id}/fetch-reviews` | POST | Yes | Fetch / replace reviews |
| `/api/businesses/{id}/reviews` | GET | Yes | List reviews |
| `/api/businesses/{id}/analyze` | POST | Yes | Run AI analysis |
| `/api/businesses/{id}/dashboard` | GET | Yes | Dashboard data |

Interactive docs: http://localhost:8000/docs

## Configuration

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/review_insight` |
| `REVIEW_PROVIDER` | Review source: `mock` or `outscraper` | `mock` |
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
| `make test-e2e` | Run E2E tests (requires `make up`) |
| `make lint` | Run linters |
| `make db-reset` | Drop all tables (backend recreates on restart) |
| `make clean` | Remove build artifacts and caches |

### Observability

The backend logs all key operations with structured fields:

- **Auth**: registration, login (success/failure)
- **Business**: creation with timing
- **Reviews**: provider fetch duration, review count, payload truncation
- **Analysis**: LLM call duration, review count, parse failures
- **Dashboard**: aggregation timing

Logs use `op=<name> duration_ms=<ms> success=<bool>` format for easy searching and monitoring. External calls (review providers, LLM) have timeouts and payload limits to fail fast instead of hanging.

### Database reset

The project uses `create_all` (no Alembic). Schema changes require dropping tables:

```bash
make db-reset
# Then restart the backend
```

## Testing

Backend tests use **pytest**:

```bash
make test           # unit tests (no server required)
make test-e2e       # end-to-end tests (requires running backend via make up)
```

### Unit tests (34 tests)

| Area | Coverage |
|------|----------|
| Provider normalization | Sample data shape, determinism, field validation, source tagging |
| Analysis normalization | Insight coercion, string normalization, missing-field defaults |
| Prompt generation | Business-type-specific prompts for all 8 types + generic fallback |
| Schema validation | Dashboard response shape, analysis fields, business type enum |

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

- [ ] Competitor comparison — side-by-side insights against linked competitor businesses
- [ ] Additional review providers — Yelp, TripAdvisor, App Store, Play Store
- [ ] Database migrations — Alembic for safe schema evolution
- [ ] Delete/archive businesses
- [ ] Secure auth — refresh tokens, httpOnly cookies
- [ ] Background jobs — Celery/Redis for async review fetching
- [ ] Export reports — PDF/CSV
- [ ] CI/CD pipeline

## License

Personal portfolio project. Not licensed for commercial use.
