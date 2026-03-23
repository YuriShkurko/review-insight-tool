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
5. Add the **frontend** service (same repo, root directory `frontend/`). This repo includes [`frontend/railway.toml`](../frontend/railway.toml) so Railway builds **`Dockerfile.prod`** (not the dev `Dockerfile`). You can also set **`RAILWAY_DOCKERFILE_PATH=Dockerfile.prod`** in Variables if needed.
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

**Empty tables are normal.** Migrations only create the schema; they do **not** insert users or businesses. With **`REVIEW_PROVIDER=offline`**, use the in-app **offline sandbox** on `/businesses` to import sample businesses into **your own account** (see below). Optional: run `seed_offline` for a pre-built demo user (CI / legacy).

## Frontend environment variables

| Variable | When | Notes |
|----------|------|--------|
| `NEXT_PUBLIC_API_URL` | **Build time** | Public backend base URL, e.g. `https://backend-production-xxxx.up.railway.app` |

Set this in Railway **before** the first successful build, or the client will call the wrong API.

### Public URL vs `PORT` (not the same thing)

- Your **frontend URL** (e.g. `https://something.up.railway.app`) comes from the **frontend** service → **Settings → Networking → Generate Domain** (or a custom domain). You do **not** need to add a **`PORT` variable** in **Variables** to “get” that URL.
- **`PORT`** is **internal**: Railway tells the **container** which TCP port your process should listen on; the **edge/proxy** then forwards public HTTPS traffic to that port. Railway usually **injects** `PORT` automatically for web services — you don’t set it to match the backend (`8000`) or to “pick” 3000 vs 8000 for the public link.
- The app must listen on **`process.env.PORT`** — [`Dockerfile.prod`](../frontend/Dockerfile.prod) runs **`node server.js`** (standalone build) with **`HOSTNAME=0.0.0.0`**. Only **remove** a **manually added** `PORT` in Variables if you added one by mistake and see 502s — it can fight Railway’s injected value.

### Railway asks “which port is the app listening on?” (Networking UI)

That prompt is **not** the same as creating a **`PORT`** env var in **Variables**. It’s Railway asking: **which port inside the container should we send traffic to?** so your public URL can reach the process.

**What to enter:**

1. Open that service → **Variables** and look for **`PORT`** (Railway often injects it automatically).
2. Use **that number** in the Networking / port field — the app and the proxy must agree.

| Service | Typical value |
|--------|----------------|
| **Frontend** (Next.js) | Same as **`PORT`** in Variables (often `3000` or whatever Railway assigns). Standalone **`server.js`** reads **`PORT`**; it must match Networking. |
| **Backend** (FastAPI) | Same as **`PORT`** in Variables. [`docker-entrypoint.sh`](../backend/docker-entrypoint.sh) uses **`${PORT:-8000}`** — so often **8000** or Railway’s `PORT`. |

**Do not** put the **backend** port (8000) on the **frontend** service (or the other way around). Each service has its own Networking settings and its own **`PORT`**.

### Still seeing **502 Bad Gateway**?

- **Confirm which URL returns 502** — frontend domain vs backend domain; fix the matching service.
- **Frontend (Next.js):** The production image runs **`node server.js`** from the **standalone** build and forces **`HOSTNAME=0.0.0.0`** so the app listens on all interfaces (Linux often sets `HOSTNAME` to the container name, which can break the proxy). Redeploy after pulling the latest [`Dockerfile.prod`](../frontend/Dockerfile.prod).
- **Networking port must match what the app prints.** If logs say **`Network: http://0.0.0.0:8080`**, Railway set **`PORT=8080`** — set **Networking → port** to **`8080`**, not **3000**. A default of 3000 while the app listens on 8080 causes **502** (proxy hits the wrong port).
- **Networking port** must match **`PORT`** for that service (see **Variables**). If they differ, the edge cannot reach your process.
- **Backend:** Uvicorn uses **`${PORT:-8000}`** — use the same port in Networking as **`PORT`** (often **8000** unless Railway overrides).

**Logs show `Stopping Container` + `npm error` + `SIGTERM`?** That usually means the **old** container was **killed** during a redeploy or restart — npm prints scary lines; it’s not necessarily an app bug. After deploying the **standalone** image, you should see **`node server.js`** in the start command, not **`next start`**.

**`Ready` then immediately `Stopping Container`?** Often either (1) a **new deploy** replacing this instance, or (2) **healthcheck / routing failure** — most commonly **Networking port ≠ `PORT`** (e.g. app on **8080**, UI still **3000**). Fix the Networking port, redeploy, and try again.

## After first deploy: offline sandbox (recommended)

1. Set **`REVIEW_PROVIDER=offline`** on the backend (curated JSON reviews; no Outscraper cost).
2. **Register** a normal user in the UI (or log in).
3. On **`/businesses`**, use **Offline sandbox** — pick sample businesses from the catalog, then open a business and run **Fetch reviews → Run analysis → Add competitors / Generate comparison** yourself.

Optional **POST `/api/sandbox/reset`** (or the **Reset offline samples** control in the catalog when shown) removes all `offline_*` businesses for the current user so you can re-run the flow.

### Optional: `seed_offline` (CI / headless / legacy)

For a pre-seeded **`demo@example.com`** account and linked businesses (bypasses the catalog UX):

1. Railway → **backend** → **Shell**.
2. `cd /app && python -m scripts.seed_offline`
3. Log in as `demo@example.com` / `demo1234`.

If the command errors on missing tables, fix **`DATABASE_URL`** and redeploy.

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
- [ ] Register / login works
- [ ] With **`REVIEW_PROVIDER=offline`**: sandbox catalog on `/businesses`; import a sample; no CORS errors
- [ ] **Fetch reviews** returns data in offline mode
- [ ] **Run analysis** works (with `OPENAI_API_KEY`) or falls back to mock
- [ ] **Competitors** — quick-add samples or manual add; **Generate comparison** when prerequisites are met
- [ ] **Remove competitor** / **Delete business** / optional **Reset offline samples**
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
- **`seed_offline`** is optional (Shell); primary offline UX is the **sandbox catalog** in the app
- E2E tests default to `localhost:8000`; point `BASE_URL` at staging if you run them remotely

## Related

- [README.md](../README.md) — Database migrations, offline demo, Makefile
- [backend/.env.example](../backend/.env.example) — all backend variables including `CORS_ORIGINS`
