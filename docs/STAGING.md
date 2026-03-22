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
| `DATABASE_URL` | Yes | **Must be Railway’s Postgres URL** — use **Variables → Add → Reference** from the PostgreSQL service (or paste the full `postgresql://…` URL). Never rely on `localhost` in the cloud; the app’s default in code is local-only. |
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

**Empty tables are normal.** Migrations only create the schema; they do **not** insert users or businesses. Populate demo data with the seed step below (or use **Register** in the UI for your own account — still no sample businesses until you add them or seed).

## Frontend environment variables

| Variable | When | Notes |
|----------|------|--------|
| `NEXT_PUBLIC_API_URL` | **Build time** | Public backend base URL, e.g. `https://backend-production-xxxx.up.railway.app` |

Set this in Railway **before** the first successful build, or the client will call the wrong API.

### Public URL vs `PORT` (not the same thing)

- Your **frontend URL** (e.g. `https://something.up.railway.app`) comes from the **frontend** service → **Settings → Networking → Generate Domain** (or a custom domain). You do **not** need to add a **`PORT` variable** in **Variables** to “get” that URL.
- **`PORT`** is **internal**: Railway tells the **container** which TCP port your process should listen on; the **edge/proxy** then forwards public HTTPS traffic to that port. Railway usually **injects** `PORT` automatically for web services — you don’t set it to match the backend (`8000`) or to “pick” 3000 vs 8000 for the public link.
- The app must listen on **`process.env.PORT`** — [`Dockerfile.prod`](../frontend/Dockerfile.prod) does that (`-p ${PORT:-3000}`) and binds **`0.0.0.0`**. Only **remove** a **manually added** `PORT` in Variables if you added one by mistake and see 502s — it can fight Railway’s injected value.

### Railway asks “which port is the app listening on?” (Networking UI)

That prompt is **not** the same as creating a **`PORT`** env var in **Variables**. It’s Railway asking: **which port inside the container should we send traffic to?** so your public URL can reach the process.

**What to enter:**

1. Open that service → **Variables** and look for **`PORT`** (Railway often injects it automatically).
2. Use **that number** in the Networking / port field — the app and the proxy must agree.

| Service | Typical value |
|--------|----------------|
| **Frontend** (Next.js) | Same as **`PORT`** in Variables (often `3000` or whatever Railway assigns). Our image listens on **`${PORT:-3000}`**, so it must match the injected `PORT`. |
| **Backend** (FastAPI) | Same as **`PORT`** in Variables. [`docker-entrypoint.sh`](../backend/docker-entrypoint.sh) uses **`${PORT:-8000}`** — so often **8000** or Railway’s `PORT`. |

**Do not** put the **backend** port (8000) on the **frontend** service (or the other way around). Each service has its own Networking settings and its own **`PORT`**.

### Still seeing **502 Bad Gateway**?

- **Confirm which URL returns 502** — frontend domain vs backend domain; fix the matching service.
- **Frontend (Next.js):** The production image runs **`node server.js`** from the **standalone** build and forces **`HOSTNAME=0.0.0.0`** so the app listens on all interfaces (Linux often sets `HOSTNAME` to the container name, which can break the proxy). Redeploy after pulling the latest [`Dockerfile.prod`](../frontend/Dockerfile.prod).
- **Networking port** must match **`PORT`** for that service (see **Variables**). If they differ, the edge cannot reach your process.
- **Backend:** Uvicorn uses **`${PORT:-8000}`** — use the same port in Networking as **`PORT`** (often **8000** unless Railway overrides).

## After first deploy: seed demo data

1. Set **`REVIEW_PROVIDER=offline`** on the backend if you want the seeded businesses to serve curated offline reviews (recommended for demos; see [README](../README.md#offline-demo-mode)).
2. Open Railway → **backend** service → **Shell** (or use a one-off command). The shell inherits **`DATABASE_URL`** from the service.
3. Run:

   ```bash
   cd /app
   python -m scripts.seed_offline
   ```

4. Log in as `demo@example.com` / `demo1234` (password set by the seed script).

If the command prints errors about missing tables, migrations did not run against this database — fix `DATABASE_URL` and redeploy, then try again.

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

## Troubleshooting

### `connection refused` to `localhost:5432` (Alembic or uvicorn)

The backend container is trying Postgres at **`localhost`**. Inside Docker, that is **this container**, not Railway’s database.

- In **Railway → backend service → Variables**, ensure **`DATABASE_URL`** is set to the **PostgreSQL plugin** connection string (reference `${{Postgres.*}}` variables or copy from the Postgres service).
- Do **not** paste your laptop’s `.env` value (`postgresql://…@localhost:5432/…`) — it will not work on Railway.
- If `DATABASE_URL` is missing, the app may fall back to the **default** in [`backend/app/config.py`](../backend/app/config.py) (`localhost`), which causes this error.

Redeploy after fixing variables.

## What is not automated

- No GitHub Actions / deploy pipeline in this repo
- No custom domain (use Railway-generated URLs or add a domain in Railway manually)
- Seeding is **manual** via Shell after deploy
- E2E tests default to `localhost:8000`; point `BASE_URL` at staging if you run them remotely

## Related

- [README.md](../README.md) — Database migrations, offline demo, Makefile
- [backend/.env.example](../backend/.env.example) — all backend variables including `CORS_ORIGINS`
