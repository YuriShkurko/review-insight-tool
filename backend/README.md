# Business Insight - Backend

FastAPI backend for the Business Insight SMB copilot. It starts by fetching Google Maps reviews, stores them in PostgreSQL, and generates AI-powered business insights using OpenAI. Supports mock, offline sandbox, simulation, and live review providers.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL running locally (or via Docker) — **not needed for tests or offline mode**

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

# Apply migrations
alembic upgrade head

# Run the server
python -m uvicorn app.main:app --reload --port 8000
```

Swagger docs available at http://localhost:8000/docs

### Running Tests

Tests use **in-memory SQLite** and force `REVIEW_PROVIDER=mock`. No Postgres, no API keys, no Docker needed.

```bash
# All tests
python -m pytest -v

# Unit tests only
python -m pytest tests/unit/ -v

# Integration tests only
python -m pytest tests/integration/ -v
```

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

#### Sandbox / Offline (requires auth)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sandbox/catalog` | List available offline demo businesses |
| POST | `/api/sandbox/import` | Import a demo scenario into the DB |
| POST | `/api/sandbox/reset` | Delete all offline businesses for the current user |

### Review Providers

Review fetching uses a pluggable provider system controlled by the `REVIEW_PROVIDER` environment variable.

| Provider | Value | Description |
|----------|-------|-------------|
| Mock | `mock` (default) | Deterministic fake reviews for development and tests |
| Offline | `offline` | Bundled JSON review files from `data/offline/` — no API key needed, used for demos |
| Outscraper | `outscraper` | Real Google Maps reviews via [Outscraper API](https://outscraper.com) |

```bash
# Mock mode (default — no keys required)
REVIEW_PROVIDER=mock

# Offline demo mode (no keys required)
REVIEW_PROVIDER=offline

# Real reviews via Outscraper
REVIEW_PROVIDER=outscraper
OUTSCRAPER_API_KEY=your-actual-key
```

Adding a new provider: create a class in `app/providers/`, implement the `ReviewProvider` interface, register it in `app/providers/factory.py`.

### Debug Flags

Two opt-in debug flags enable E2E request tracing and the MCP debug server. Both are off by default and safe to leave unset in production.

| Flag | Values | Description |
|------|--------|-------------|
| `DEBUG_TRACE` | `true` / unset | Enables in-memory request trace ring buffer (500 traces × 50 spans). Every request gets an `X-Trace-Id` header propagated end-to-end. |
| `DEBUG_MCP` | `true` / unset | Enables the stdio MCP debug server (`python -m debug.mcp_server`). Exposes 13 read-only introspection tools. |

```bash
# Start backend with tracing enabled
DEBUG_TRACE=true python -m uvicorn app.main:app --reload --port 8000

# Start the MCP debug server (separate process, stdio transport)
DEBUG_MCP=true python -m debug.mcp_server
```

**Tracing tools (require `DEBUG_TRACE=true`):**

| MCP Tool | Description |
|----------|-------------|
| `trace_journey(trace_id)` | Full ordered span tree for one request |
| `recent_traces(limit)` | Last N traces, newest first |
| `mutation_log(entity_id)` | All write-flagged spans for a business/entity |
| `llm_call_log(business_id)` | All LLM call spans for a business |
| `health_probe()` | DB ping + provider + trace buffer status |

**Tuning env vars (all optional, safe defaults):**

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG_TRACE_MAX_TRACES` | `500` | Ring buffer capacity (traces) |
| `DEBUG_TRACE_MAX_SPANS` | `50` | Max spans stored per trace |
| `DEBUG_TRACE_SAMPLE_RATE` | `1.0` | Fraction of requests traced (0.0–1.0, hash-deterministic) |
| `DEBUG_TRACE_TTL_HOURS` | `24` | Traces older than this are auto-evicted |

### Project Structure

```
backend/
├── app/
│   ├── main.py              # App entry point
│   ├── config.py            # Environment settings (reads .env)
│   ├── database.py          # SQLAlchemy engine and session setup
│   ├── auth.py              # JWT auth and password hashing
│   ├── models/              # ORM models (User, Business, Review, Analysis, CompetitorLink)
│   ├── schemas/             # Pydantic request/response models
│   ├── routes/              # API route handlers
│   ├── services/            # Business logic layer
│   └── providers/           # Review source provider abstraction
│       ├── base.py          # ReviewProvider interface + NormalizedReview type
│       ├── factory.py       # Provider selection based on REVIEW_PROVIDER
│       ├── mock_provider.py # Deterministic fake reviews
│       ├── offline_provider.py  # Bundled JSON reviews (demo/sandbox)
│       └── outscraper_provider.py  # Real Google Maps reviews
├── data/
│   └── offline/             # Bundled review files for offline/demo mode
│       ├── manifest.json    # Scenario and business catalogue
│       └── *_reviews.json   # Per-business review data
├── debug/                   # MCP debug server (local only, never deployed)
│   ├── mcp_server.py        # FastMCP stdio entry point (requires DEBUG_MCP=true)
│   └── tools.py             # 8 introspection tools (system_status, business_snapshot, …)
├── tests/
│   ├── unit/                # Pure unit tests (no DB)
│   └── integration/         # API-level tests (in-memory SQLite, no Postgres needed)
├── alembic/                 # DB migration scripts
├── requirements.txt
└── .env.example
```
