# Staging / demo deployment (Railway)

This document describes a **manual** way to run Review Insight Tool on [Railway](https://railway.app) for staging or demos. It does **not** set up CI/CD or automated deploys.

## Why Railway (recommended for solo projects)

- Deploy from GitHub with per-service **root directories** (`backend/`, `frontend/`)
- Managed **PostgreSQL** plugin
- **Environment variables** in the dashboard (available at build time for the frontend)
- **Migrations on container start** — backend [`docker-entrypoint.sh`](../backend/docker-entrypoint.sh) runs `alembic upgrade head` before uvicorn (no separate Railway command required)
- Low friction compared to wiring your own VPS

## Architecture

- **PostgreSQL** — Railway plugin; exposes `DATABASE_URL` to linked services
- **Backend** — Docker build from `backend/` ([Dockerfile](../backend/Dockerfile)); listens on **`PORT`** (set by Railway)
- **Frontend** — Docker build from `frontend/` using [`Dockerfile.prod`](../frontend/Dockerfile.prod); **`NEXT_PUBLIC_API_URL`** is **build-time**; Next.js listens on **`PORT`**

## Order of setup (important)

`NEXT_PUBLIC_API_URL` is **baked into the frontend at `npm run build`**. `CORS_ORIGINS` must match the **final** frontend origin. Follow this order:

1. Create a Railway project and add the **PostgreSQL** plugin.
2. Add the **backend** service (GitHub repo, root directory `backend/`).
3. **Generate a public URL** for the backend (Settings → Networking → Generate Domain). You need this URL before building the frontend.
4. Configure backend env vars (see below). Leave **`CORS_ORIGINS` empty** until step 8.
5. Add the **frontend** service (same repo, root directory `frontend/`, set **`RAILWAY_DOCKERFILE_PATH=Dockerfile.prod`** if both Dockerfiles exist).
6. Set **`NEXT_PUBLIC_API_URL`** to `https://<your-backend-host>` (must include `https://`).
7. **Generate a public URL** for the frontend.
8. Set **`CORS_ORIGINS`** on the backend to `https://<your-frontend-host>` (exact origin, no trailing slash unless your app uses it).
9. **Redeploy** both services if needed so CORS and the frontend build stay in sync.

Do **not** set a custom start command on the backend unless you know what you’re doing — the image already runs migrations then uvicorn. If you previously set `alembic upgrade head && uvicorn ...`, remove it to avoid confusion (running Alembic twice is harmless but redundant).

If you change the backend URL after the first frontend build, **rebuild/redeploy the frontend** so `NEXT_PUBLIC_API_URL` is correct.

## Backend environment variables

| Variable | Required | Notes |
|----------|----------|--------|
| `DATABASE_URL` | Yes | From PostgreSQL plugin (reference variable) or paste connection string |
| `REVIEW_PROVIDER` | Recommended | `offline` for demos (no Outscraper cost) |
| `JWT_SECRET_KEY` | Yes | Random string, 32+ characters |
| `OPENAI_API_KEY` | Optional | Omit for mock analysis; set for real AI output |
| `CORS_ORIGINS` | For remote UI | Comma-separated frontend origins, e.g. `https://xxx.up.railway.app` |
| `OUTSCRAPER_*` | If using Outscraper | Only when `REVIEW_PROVIDER=outscraper` |

Railway injects **`PORT`** — do not set it manually unless debugging.

## Migrations (backend)

The backend Docker image runs **`alembic upgrade head`** in [`docker-entrypoint.sh`](../backend/docker-entrypoint.sh) **before** starting uvicorn. You do **not** need a Railway “Custom Start Command” for normal deploys.

**Migrate-on-start is acceptable for single-instance staging** (one replica). Alembic is a no-op when already at head. For **multiple app instances**, run migrations in a **one-off job** before rolling out new replicas to avoid concurrent migration races.

**Optional:** If you prefer not to migrate on start, you could override the container entrypoint in Railway (advanced); then run `alembic upgrade head` manually in **Shell** after deploys.

## Frontend environment variables

| Variable | When | Notes |
|----------|------|--------|
| `NEXT_PUBLIC_API_URL` | **Build time** | Public backend base URL, e.g. `https://backend-production-xxxx.up.railway.app` |

Set this in Railway **before** the first successful build, or the client will call the wrong API.

## After first deploy: seed demo data

1. Open Railway → **backend** service → **Shell** (or use a one-off command).
2. Run:

   ```bash
   python -m scripts.seed_offline
   ```

3. Log in as `demo@example.com` / `demo1234` (see [offline demo](../README.md#offline-demo-mode)).

## Local Docker Compose (unchanged)

`docker compose` still uses **hot reload** on the backend via `command:` override in [`docker-compose.yml`](../docker-compose.yml). CORS defaults include localhost; set `CORS_ORIGINS` only when testing remote origins locally.

## One-time: existing DB without Alembic version

If `alembic upgrade head` fails with **`relation "users" already exists`**, stamp once:

```bash
alembic stamp head
```

Then run `alembic upgrade head` for future migrations only.

## Staging smoke test checklist

- [ ] Frontend loads at the public URL (no blank page)
- [ ] Register works; or login works with seeded demo user
- [ ] Demo login: `demo@example.com` / `demo1234` (after seed)
- [ ] `/businesses` lists businesses; no CORS errors in browser console
- [ ] Business detail page loads (metadata, actions)
- [ ] **Fetch reviews** returns data in offline mode for seeded businesses
- [ ] **Run analysis** works (with `OPENAI_API_KEY`) or falls back to mock
- [ ] **Competitors** section loads; **Generate comparison** works when prerequisites are met
- [ ] **Remove competitor** succeeds without a false error
- [ ] **Delete business** from list works
- [ ] Backend logs visible in Railway (Observability / Logs)

## What is not automated

- No GitHub Actions / deploy pipeline in this repo
- No custom domain (use Railway-generated URLs or add a domain in Railway manually)
- Seeding is **manual** via Shell after deploy
- E2E tests default to `localhost:8000`; point `BASE_URL` at staging if you run them remotely

## Related

- [README.md](../README.md) — Database migrations, offline demo, Makefile
- [backend/.env.example](../backend/.env.example) — all backend variables including `CORS_ORIGINS`
