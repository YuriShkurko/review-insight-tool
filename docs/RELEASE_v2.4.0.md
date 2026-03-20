# v2.4.0 — Alembic Migrations and Staging Readiness

## What's New

### Database migrations (Alembic)
- **PostgreSQL schema** is managed with **Alembic** instead of `SQLAlchemy.create_all()` on app startup
- Initial revision `96daf85753e5` creates the current tables: `users`, `businesses`, `reviews`, `analyses`, `competitor_links`
- Follow-up revision `e273fafbe8de` adds nullable `businesses.notes` (validates autogenerate → upgrade → downgrade path; field not exposed in API yet)
- `alembic/env.py` uses the same `DATABASE_URL` as the FastAPI app (`app.config`)
- New dependency: `alembic>=1.14.0` in `backend/requirements.txt`

### Developer workflow (Makefile)
- `make db-upgrade` — apply migrations to head
- `make db-downgrade` — roll back one revision
- `make db-current` / `make db-history` — inspect state
- `make db-revision msg="..."` — autogenerate a new revision (review the file before committing)
- `make db-stamp-head` — one-time: mark an **existing** pre-Alembic database at head without re-running DDL
- `make db-reset` — also drops `alembic_version` (then run `make db-upgrade` for a clean schema)

### App / scripts
- **Removed** `create_all` from **`app/main.py`** lifespan — run migrations before or after deploy
- **Removed** `create_all` from **`scripts/seed_offline.py`** — seed expects schema from migrations; clear error if tables are missing
- **Integration tests** still use `create_all` on **in-memory SQLite** only (documented in `conftest.py`)

### Documentation
- README: Quick Start and offline flow include **`make db-upgrade`**; new **Database migrations** section (including **DuplicateTable** → **`make db-stamp-head`**)
- **docs/SPEC.md**: version 1.4, **Database migrations** section, limitations/roadmap updated
- **docs/STAGING.md**: recommended staging/demo order (deploy → env → `alembic upgrade head` → optional seed → smoke), env var table, CORS note
- **backend/.env.example**: note that Alembic uses `DATABASE_URL`
- Roadmap: **Database migrations** item marked done

## Upgrade Notes

- **New empty database:** `make up` → `make db-upgrade` → optional `make seed-offline`
- **Existing local Docker volume** (tables already existed from old `create_all`): if `make db-upgrade` fails with **`relation "users" already exists`**, run **`make db-stamp-head` once**, then `make db-upgrade` stays at head until new migrations ship
- **Data is preserved** by migrations; `db-upgrade` does not wipe user/business rows unless a future migration explicitly does

## Breaking Changes

- **Operational:** The backend **no longer** creates tables automatically on startup. Anyone using Docker or local Postgres must run **`alembic upgrade head`** (or **`make db-upgrade`**) after pulling this version (and use **`make db-stamp-head`** once if upgrading from a DB that already had tables but no `alembic_version` row).

## Full Changelog

v2.3.0...v2.4.0
