# v2.5.0 — Remote staging (Railway): CORS, PORT, production frontend image

## What's New

### Staging / demo deployment (Railway-oriented)
- **`CORS_ORIGINS`** — comma-separated extra allowed origins in [`backend/app/config.py`](../backend/app/config.py); merged with localhost defaults in [`backend/app/main.py`](../backend/app/main.py). Set to your public frontend URL (e.g. `https://….up.railway.app`) for remote UI.
- **Platform `PORT`** — backend [`Dockerfile`](../backend/Dockerfile) uses shell `CMD` with `${PORT:-8000}` so PaaS-injected `PORT` is respected; `ENV PORT=8000` as default for local runs.
- **Local dev unchanged** — [`docker-compose.yml`](../docker-compose.yml) overrides the backend with **`command:`** including **`--reload`** (hot reload only for Compose).
- **Production frontend image** — [`frontend/Dockerfile.prod`](../frontend/Dockerfile.prod): multi-stage `npm run build` + `npm start`; **`ARG`/`ENV` `NEXT_PUBLIC_API_URL`** before build (bakes API base URL into the client); **`PORT`** for Next.js.

### Documentation
- **[docs/STAGING.md](STAGING.md)** — Railway-focused manual flow: **order of setup** (backend domain → `NEXT_PUBLIC_API_URL` → frontend domain → `CORS_ORIGINS`), env tables, custom start command with **`alembic upgrade head`**, note that **migrate-on-start is for single-instance staging only**, smoke-test checklist, what remains manual / not automated.
- **[README.md](../README.md)** — Development section links to staging doc; project tree lists `Dockerfile.prod`.
- **[backend/.env.example](../backend/.env.example)** — documents `CORS_ORIGINS`.

## Upgrade Notes

- **Local Docker Compose:** `make up` — backend still uses reload via Compose `command:`; no `.env` change required unless testing remote CORS locally.
- **New deploys (Railway or similar):** set `DATABASE_URL`, `JWT_SECRET_KEY`, `REVIEW_PROVIDER`, optional `OPENAI_API_KEY`, then `CORS_ORIGINS` after the frontend URL exists; build frontend with `NEXT_PUBLIC_API_URL` pointing at the public backend URL.

## Breaking Changes

None for API contracts. **Operational:** default backend Docker image no longer runs `--reload`; Compose supplies reload for local dev.

## Full Changelog

v2.4.0...v2.5.0
