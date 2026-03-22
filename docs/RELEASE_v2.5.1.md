# v2.5.1 — Migrate on container start (Railway-friendly)

## What's New

### Backend Docker image
- **`backend/docker-entrypoint.sh`** runs **`alembic upgrade head`** before starting uvicorn, using **`PORT`** from the platform (default **8000**).
- **`backend/Dockerfile`** uses **`ENTRYPOINT`**; local **`docker-compose`** still overrides with **`command:`** so **`--reload`** works (migrations run on each backend container start locally too — usually a no-op).

### Documentation
- **`docs/STAGING.md`** — Railway no longer needs a duplicate custom start command for Alembic; optional **`RAILWAY_DOCKERFILE_PATH=Dockerfile.prod`** for the frontend; step order tweaks.
- **`README.md`** — notes production image behavior under Database migrations; project structure lists **`docker-entrypoint.sh`**.

## Operational notes

- **Single-instance staging:** migrate-on-start remains acceptable; for **multiple replicas**, use a one-off migration job instead.
- **Railway:** remove any previous **`alembic upgrade head && uvicorn ...`** custom start command to avoid redundant runs (still harmless).

## Full Changelog

v2.5.0...v2.5.1
