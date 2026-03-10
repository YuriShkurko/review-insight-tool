# Review Insight Tool

An AI-powered review analysis platform for small businesses. Paste a Google Maps link, fetch real customer reviews, and get actionable business insights — tailored to your business type.

Built as a full-stack portfolio project with FastAPI, Next.js, PostgreSQL, and OpenAI.

## Screenshots

| Login | Add Business | Dashboard |
|-------|-------------|-----------|
| ![Login](docs/screenshots/01-login.png) | ![Add Business](docs/screenshots/02-add-business.png) | ![Dashboard](docs/screenshots/03-dashboard.png) |

| Insights & Actions | Reviews |
|--------------------|---------|
| ![Insights](docs/screenshots/04-insights.png) | ![Reviews](docs/screenshots/05-reviews.png) |

## Problem & Motivation

Small business owners receive hundreds of reviews across platforms but rarely have time to read them all, spot patterns, or turn feedback into action. Review Insight Tool solves this by:

- **Aggregating reviews** from Google Maps into a single view
- **Surfacing patterns** — what customers love and what frustrates them
- **Generating actionable recommendations** tailored to the specific business type (a restaurant gets different insights than a gym or salon)
- **Saving hours** of manual review reading with AI-powered analysis

## Features

| Feature | Description |
|---------|-------------|
| **Business onboarding** | Paste a Google Maps URL, select a business type, and the app extracts the place ID and name automatically |
| **Review ingestion** | Pluggable provider architecture — mock data for development, Outscraper for real Google Maps reviews |
| **Clean refresh** | Re-fetching reviews replaces the old set and clears stale analysis for a trustworthy single source of truth |
| **Business-type-aware AI analysis** | LLM prompts are tailored per business type (restaurant, bar, cafe, gym, salon, hotel, clinic, retail) |
| **Rich insights** | Summary, top complaints, top praise, action items, risk areas, and a recommended focus area |
| **Dashboard** | Average rating, review count, AI summary, and categorized insights in one view |
| **User auth** | JWT-based registration and login; each user sees only their own data |

## Architecture

```mermaid
graph LR
    User([User]) --> Frontend

    subgraph Client
        Frontend[Next.js Frontend<br/>React · TypeScript · Tailwind]
    end

    subgraph Server
        API[FastAPI Backend<br/>Routes · Services · Auth]
        Providers[Review Providers<br/>Mock · Outscraper · ...]
        LLM[LLM Analysis<br/>OpenAI GPT-4o-mini]
    end

    subgraph Data
        DB[(PostgreSQL<br/>Users · Businesses<br/>Reviews · Analyses)]
    end

    Frontend -- HTTP/JSON --> API
    API --> Providers
    API --> LLM
    API --> DB
```

**Backend** follows a layered pattern:

| Layer | Responsibility |
|-------|---------------|
| **Routes** | Thin HTTP handlers, input validation, auth enforcement |
| **Services** | Business logic — place resolution, review ingestion, AI analysis, dashboard assembly |
| **Providers** | Pluggable review source abstraction (mock, Outscraper, future: Yelp, etc.) |
| **Models** | SQLAlchemy ORM — User, Business, Review, Analysis |
| **Schemas** | Pydantic request/response validation |

**Frontend** follows a 3-layer pattern:

| Layer | Responsibility |
|-------|---------------|
| **Pages** | Next.js App Router pages with client-side data fetching |
| **Components** | Small, reusable UI pieces — DashboardView, ReviewList, InsightList, etc. |
| **Lib** | API client, auth context, TypeScript types |

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2.0, Pydantic |
| Frontend | Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS 4 |
| Database | PostgreSQL 16 |
| AI | OpenAI GPT-4o-mini |
| Auth | JWT (PyJWT), bcrypt |
| Review providers | Mock (built-in), Outscraper |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker (for PostgreSQL)

### 1. Start PostgreSQL

```bash
docker run --name review-insight-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=review_insight \
  -p 5432:5432 \
  -d postgres:16
```

### 2. Backend

```bash
cd backend

python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # macOS / Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env if needed — defaults work for local development with mock data

python -m uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000 — Swagger docs at http://localhost:8000/docs

### 3. Frontend

```bash
cd frontend

npm install

cp .env.local.example .env.local

npm run dev
```

Frontend runs at http://localhost:3000

### Using Make (optional)

If you have `make` available, you can use the provided Makefile:

```bash
make backend    # start backend server
make frontend   # start frontend dev server
make test       # run backend tests
make lint       # run linters
```

## Usage

The core workflow in 5 steps:

1. **Register** — Create an account at `/register`
2. **Add a business** — Paste a Google Maps URL and select the business type (restaurant, bar, cafe, gym, salon, hotel, clinic, retail, or other)
3. **Fetch reviews** — Click "Fetch Reviews" to pull customer reviews via the configured provider
4. **Run analysis** — Click "Run Analysis" to generate AI-powered insights tailored to the business type
5. **View dashboard** — See average rating, AI summary, recommended focus, top complaints, top praise, action items, and risk areas

> **Tip:** Use the **Share > Copy link** button on Google Maps to get a reliable URL. Search-bar URLs may not contain the required place ID.

## API

All endpoints are prefixed with `/api`. Business, review, analysis, and dashboard endpoints require a `Bearer` token in the `Authorization` header.

| Endpoint | Method | Auth | Description |
|----------|--------|------|-------------|
| `/api/auth/register` | POST | No | Create account |
| `/api/auth/login` | POST | No | Sign in, receive JWT |
| `/api/auth/me` | GET | Yes | Current user info |
| `/api/businesses` | POST | Yes | Add business |
| `/api/businesses` | GET | Yes | List user's businesses |
| `/api/businesses/{id}` | GET | Yes | Get business details |
| `/api/businesses/{id}/fetch-reviews` | POST | Yes | Fetch/replace reviews |
| `/api/businesses/{id}/reviews` | GET | Yes | List reviews |
| `/api/businesses/{id}/analyze` | POST | Yes | Run AI analysis |
| `/api/businesses/{id}/dashboard` | GET | Yes | Get dashboard data |

Interactive API docs: http://localhost:8000/docs

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/review_insight` |
| `REVIEW_PROVIDER` | Review source: `mock` or `outscraper` | `mock` |
| `OUTSCRAPER_API_KEY` | Outscraper API key (required when provider = outscraper) | — |
| `OPENAI_API_KEY` | OpenAI API key (blank = mock analysis) | — |
| `GOOGLE_PLACES_API_KEY` | Google Places API key (blank = extract name from URL) | — |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | `change-me-in-production` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `1440` |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `http://localhost:8000` |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Pydantic settings from environment
│   │   ├── database.py          # SQLAlchemy engine and session
│   │   ├── auth.py              # JWT + bcrypt auth utilities
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── routes/              # API route handlers
│   │   ├── services/            # Business logic layer
│   │   ├── providers/           # Pluggable review source providers
│   │   └── mock/                # Mock data generators
│   ├── tests/                   # pytest test suite
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   ├── components/          # Reusable React components
│   │   └── lib/                 # API client, auth, types
│   ├── package.json
│   └── .env.local.example
│
├── docs/screenshots/            # README screenshots
├── Makefile                     # Developer shortcuts
└── README.md
```

## Development

### Backend development

```bash
cd backend
source venv/bin/activate  # or venv\Scripts\activate on Windows
python -m uvicorn app.main:app --reload --port 8000
```

The `--reload` flag enables hot-reloading on file changes.

### Frontend development

```bash
cd frontend
npm run dev
```

### Database reset

Since the project uses `create_all` (no Alembic migrations), schema changes require a manual reset:

```bash
docker exec -i review-insight-db psql -U postgres -d review_insight \
  -c "DROP TABLE IF EXISTS analyses, reviews, businesses, users CASCADE;"
```

Restart the backend to recreate tables.

## Testing

Backend tests use **pytest**:

```bash
cd backend
pip install pytest
python -m pytest tests/ -v
```

Tests cover:
- Mock provider review normalization and determinism
- Analysis result normalization
- Business-type-aware prompt generation
- Dashboard response schema validation

## Roadmap

- [ ] **Competitor comparison** — link competitor Google Maps pages and get side-by-side insights with improvement suggestions
- [ ] **Additional review providers** — Yelp, TripAdvisor, App Store, Play Store
- [ ] **Database migrations** — Alembic for safe schema evolution
- [ ] **Delete/archive businesses** — remove or archive businesses from the dashboard
- [ ] **Secure auth** — refresh tokens, httpOnly cookies, password strength enforcement
- [ ] **Background jobs** — Celery/Redis for async review fetching
- [ ] **Export reports** — PDF/CSV export of analysis results
- [ ] **Deployment** — Docker Compose, CI/CD pipeline

## License

This is a personal portfolio project. Not licensed for commercial use.
