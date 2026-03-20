# Staging / demo deployment

This document describes a minimal, **manual** flow to run Review Insight Tool on a remote host for staging or demos. It does **not** set up CI/CD or automated deploys.

## Recommended order

1. **Provision** PostgreSQL 16+ and deploy the backend (FastAPI) and frontend (Next.js) containers or processes.
2. **Configure environment** on the backend (see below). Prefer **`REVIEW_PROVIDER=offline`** for demos so review fetching does not depend on Outscraper credits or Google Maps availability.
3. **Run migrations** against the production/staging database (same `DATABASE_URL` the app will use):

   ```bash
   cd backend
   alembic upgrade head
   ```

4. **Seed demo data** (optional, for a predictable walkthrough):

   ```bash
   python -m scripts.seed_offline
   ```

5. **Smoke the app**: open the frontend URL, log in as `demo@example.com` / `demo1234` (if seeded), fetch reviews for a seeded business, run analysis, optionally generate a competitor comparison.

6. **Automated smoke** (optional): with the backend URL reachable, run `make test-e2e` from a machine that points tests at that API (today E2E assumes `localhost:8000`; adjust or run manually if the host differs).

## Environment variables (backend)

| Variable | Staging / demo | Notes |
|----------|----------------|-------|
| `DATABASE_URL` | **Required** | PostgreSQL connection string used by the app and by `alembic`. |
| `REVIEW_PROVIDER` | **`offline` recommended** | Avoids Outscraper cost/latency for demos. Use `outscraper` only if you need live Maps reviews. |
| `JWT_SECRET_KEY` | **Required** | Use a long random string (32+ characters). Do not use the example default. |
| `OPENAI_API_KEY` | Optional for UI analysis | Without it, analysis falls back to mock/sample behavior. Set for real AI output. |
| `OUTSCRAPER_API_KEY` | Only if `REVIEW_PROVIDER=outscraper` | |
| `OUTSCRAPER_REVIEWS_LIMIT`, `OUTSCRAPER_SORT`, `OUTSCRAPER_CUTOFF` | Optional | Tune real-provider fetches. |

Frontend: set `NEXT_PUBLIC_API_URL` to the **public** backend base URL (e.g. `https://api.example.com`).

## CORS

[backend/app/main.py](../backend/app/main.py) allows `localhost` origins by default. For a remote staging URL, add your frontend origin to `CORSMiddleware` `allow_origins` (small code change) or use a reverse proxy that serves both under one host.

## One-time: existing DB built with old `create_all`

If the database already has the correct tables but no `alembic_version` row, stamp once instead of running the initial migration:

```bash
alembic stamp head
```

If you run `alembic upgrade head` first and see **`DuplicateTable` / `relation "users" already exists`**, the database is in this state — use `stamp head` (or `make db-stamp-head` with Docker Compose) and do not re-run the failed `upgrade`.

New empty databases should use `alembic upgrade head` only.

## Related

- Local migration workflow: [README.md](../README.md) — **Database migrations**
- Makefile shortcuts (Docker): `make db-upgrade`, `make db-stamp-head`, `make seed-offline`
