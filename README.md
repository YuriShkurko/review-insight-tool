# Review Insight Tool

A micro-SaaS that lets business owners paste a Google Maps link, fetch customer reviews, and get AI-powered analysis — including average rating, top complaints, top praise, and a natural-language summary.

Built as a full-stack portfolio project demonstrating a clean, production-style architecture with FastAPI, Next.js, PostgreSQL, and OpenAI.

## Screenshots

| Login | Add Business | Dashboard |
|-------|-------------|-----------|
| ![Login](docs/screenshots/01-login.png) | ![Add Business](docs/screenshots/02-add-business.png) | ![Dashboard](docs/screenshots/03-dashboard.png) |

| Insights & Actions | Reviews |
|--------------------|---------|
| ![Insights](docs/screenshots/04-insights.png) | ![Reviews](docs/screenshots/05-reviews.png) |

## Core Features

- **Add a business** — Paste any Google Maps URL; select business type (restaurant, bar, cafe, gym, salon, hotel, clinic, retail, or other)
- **Fetch reviews** — Pluggable provider system: mock data for development, Outscraper for real Google Maps reviews
- **Clean refresh** — Re-fetching reviews replaces the old set entirely and clears stale analysis
- **Business-type-aware AI analysis** — Generates summary, top complaints, top praise, action items, risk areas, and a recommended focus area using prompts tailored to the business type
- **Dashboard** — Displays average rating, review count, AI summary, recommended focus, categorized insights, action items, and risk areas
- **User auth** — JWT-based registration and login; each user sees only their own businesses

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python, FastAPI, SQLAlchemy, Pydantic, Outscraper |
| Frontend | Next.js (App Router), React, TypeScript, Tailwind CSS |
| Database | PostgreSQL |
| AI | OpenAI GPT-4o-mini |
| Auth | JWT (PyJWT), bcrypt |

## Architecture

```
┌─────────────┐     HTTP/JSON     ┌─────────────────┐     SQL     ┌────────────┐
│   Next.js   │ ◄──────────────► │    FastAPI       │ ◄────────► │ PostgreSQL │
│  Frontend   │                   │    Backend       │             │            │
└─────────────┘                   └───────┬─┬───────┘             └────────────┘
                                          │ │
                                OpenAI ───┘ └─── Review Providers
                               (optional)       (mock / outscraper / ...)
```

**Backend** follows a layered pattern:
- **Routes** — Thin HTTP handlers, input validation, auth enforcement
- **Services** — Business logic (place resolution, review ingestion, AI analysis, dashboard assembly)
- **Providers** — Pluggable review source abstraction (mock, Outscraper, future: Yelp, etc.)
- **Models** — SQLAlchemy ORM (User, Business, Review, Analysis)
- **Schemas** — Pydantic request/response shapes

**Frontend** follows a 3-layer pattern:
- **Pages** — Next.js App Router pages with client-side data fetching
- **Components** — Small, reusable UI pieces (DashboardView, ReviewList, InsightList, etc.)
- **Lib** — API client, auth context, TypeScript types

## Local Setup

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
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

pip install -r requirements.txt

cp .env.example .env
# Edit .env if needed (defaults work for local development)

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

## Environment Variables

### Backend (`backend/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/review_insight` |
| `REVIEW_PROVIDER` | Review source: `mock` or `outscraper` | `mock` |
| `OUTSCRAPER_API_KEY` | Outscraper API key (required when provider = outscraper) | ` ` |
| `OPENAI_API_KEY` | OpenAI API key (blank = mock analysis) | ` ` |
| `GOOGLE_PLACES_API_KEY` | Google Places API key (blank = extract from URL) | ` ` |
| `JWT_SECRET_KEY` | Secret for signing JWT tokens | `change-me-in-production` |
| `JWT_EXPIRE_MINUTES` | Token expiry in minutes | `1440` (24 hours) |

### Frontend (`frontend/.env.local`)

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_API_URL` | Backend base URL | `http://localhost:8000` |

## API Overview

All endpoints are prefixed with `/api`. Business, review, analysis, and dashboard endpoints require a `Bearer` token in the `Authorization` header.

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create account |
| `/api/auth/login` | POST | Sign in |
| `/api/auth/me` | GET | Current user |
| `/api/businesses` | POST | Add business |
| `/api/businesses` | GET | List businesses |
| `/api/businesses/{id}` | GET | Get business |
| `/api/businesses/{id}/fetch-reviews` | POST | Fetch reviews |
| `/api/businesses/{id}/reviews` | GET | List reviews |
| `/api/businesses/{id}/analyze` | POST | Run AI analysis |
| `/api/businesses/{id}/dashboard` | GET | Dashboard data |

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app entry point
│   │   ├── config.py            # Settings from environment
│   │   ├── database.py          # SQLAlchemy engine and session
│   │   ├── auth.py              # JWT + bcrypt auth utilities
│   │   ├── models/              # SQLAlchemy ORM models
│   │   ├── schemas/             # Pydantic validation schemas
│   │   ├── routes/              # API route handlers
│   │   ├── services/            # Business logic layer
│   │   ├── providers/           # Pluggable review source providers
│   │   └── mock/                # Mock data generators
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
└── README.md
```

## Current Limitations (V1.1)

- **Outscraper costs** — Outscraper is a paid API; mock mode is free and used by default
- **No real-time updates** — Dashboard must be manually refreshed after actions
- **No database migrations** — Schema changes require a full database reset (`DROP` and recreate)
- **Token in localStorage** — Acceptable for V1 but not suitable for production
- **No password requirements** — No minimum length or complexity enforcement
- **Single-user focus** — No teams, roles, or shared access
- **No delete** — Businesses cannot be removed once added
- **Review refresh replaces all** — Refreshing reviews deletes the old set and clears analysis; there is no incremental update

## Future Improvements

- Competitor comparison — compare your business insights against linked competitors
- Additional review providers (Yelp, TripAdvisor, App Store, Play Store)
- Add Alembic for database migrations
- Add delete/archive business functionality
- Implement refresh tokens and httpOnly cookies
- Add password strength requirements
- Background job processing for review fetching (Celery/Redis)
- Deployment configuration (Docker Compose, CI/CD)
- Export analysis reports (PDF/CSV)

## License

This is a personal portfolio project. Not licensed for commercial use.
