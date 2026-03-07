# Review Insight Tool — Backend

FastAPI backend that fetches Google Maps reviews, stores them in PostgreSQL, and generates AI-powered insights using OpenAI.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL running locally (or via Docker)

### Database Setup (Docker)

```bash
docker run --name review-insight-db \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=review_insight \
  -p 5432:5432 \
  -d postgres:16
```

### Setup

```bash
cd backend

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your database URL and API keys

# Run the server
python -m uvicorn app.main:app --reload --port 8000
```

Swagger docs available at http://localhost:8000/docs

### API Endpoints

#### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Create a new user account |
| POST | `/api/auth/login` | Sign in, receive JWT token |
| GET | `/api/auth/me` | Get current user info |

#### Businesses (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/businesses` | Add a business by place ID or Google Maps URL |
| GET | `/api/businesses` | List your businesses |
| GET | `/api/businesses/{id}` | Get a single business |

#### Reviews & Analysis (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/businesses/{id}/fetch-reviews` | Fetch and store reviews |
| GET | `/api/businesses/{id}/reviews` | List stored reviews |
| POST | `/api/businesses/{id}/analyze` | Run AI analysis on reviews |
| GET | `/api/businesses/{id}/dashboard` | Get full dashboard data |

### Review Providers

Review fetching uses a pluggable provider system controlled by the `REVIEW_PROVIDER` environment variable.

| Provider | Value | Description |
|----------|-------|-------------|
| Mock | `mock` (default) | Deterministic fake reviews for development |
| Outscraper | `outscraper` | Real Google Maps reviews via [Outscraper API](https://outscraper.com) |

To switch providers, set `REVIEW_PROVIDER` in `.env`:

```bash
# Mock mode (default)
REVIEW_PROVIDER=mock

# Real reviews via Outscraper
REVIEW_PROVIDER=outscraper
OUTSCRAPER_API_KEY=your-actual-key
```

Adding a new provider later is straightforward: create a provider class in `app/providers/`, implement the `ReviewProvider` interface, and register it in `app/providers/factory.py`.

### Project Structure

```
backend/
├── app/
│   ├── main.py              # App entry point
│   ├── config.py            # Environment settings
│   ├── database.py          # SQLAlchemy setup
│   ├── auth.py              # JWT auth and password hashing
│   ├── models/              # ORM models (User, Business, Review, Analysis)
│   ├── schemas/             # Pydantic request/response models
│   ├── routes/              # API route handlers
│   ├── services/            # Business logic layer
│   ├── providers/           # Review source provider abstraction
│   │   ├── base.py          # ReviewProvider interface + NormalizedReview type
│   │   ├── factory.py       # Provider selection based on config
│   │   ├── mock_provider.py # Mock reviews for development
│   │   └── outscraper_provider.py  # Real Google Maps reviews
│   └── mock/                # Mock data generators
├── requirements.txt
└── .env.example
```
