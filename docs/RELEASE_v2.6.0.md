# v2.6.0 — Offline Sandbox Catalog, Ruff + Prettier Tooling

## What's New

### Offline Sandbox
- New **sandbox catalog** replaces the seeded demo user as the primary offline/demo experience
- Three API endpoints power the flow:
  - `GET /api/sandbox/catalog` — returns the offline manifest as browsable scenarios and standalone businesses, enriched with the current user's import status
  - `POST /api/sandbox/import` — imports a sample business into the authenticated user's account; optionally links it as a competitor via `as_competitor_for`
  - `POST /api/sandbox/reset` — deletes all `offline_`-prefixed businesses owned by the current user
- New Pydantic schemas: `CatalogBusiness`, `CatalogScenario`, `CatalogResponse`, `SandboxImport`, `SandboxResetResponse`
- `DashboardResponse` now includes `place_id` so the frontend can match dashboard state to catalog entries
- `seed_offline.py` still works for headless/CI seeding but is no longer the recommended demo path

### Frontend
- **`SandboxCatalog`** component on the businesses list page — full variant when no businesses exist, compact variant when they do
- **Quick-add competitors** from the offline catalog on the business detail page via `CompetitorSection`
- New TypeScript types: `CatalogBusiness`, `CatalogScenario`, `CatalogResponse` in `frontend/src/lib/types.ts`
- Auth init effect refactored to satisfy the stricter `react-hooks/set-state-in-effect` rule

### Tooling
- **[Ruff](https://docs.astral.sh/ruff/)** added for Python lint + format — config in [`backend/pyproject.toml`](../backend/pyproject.toml)
  - Rules: pyflakes, pycodestyle, isort, pep8-naming, pyupgrade, flake8-bugbear, flake8-simplify, flake8-print, ruff-specific
  - Per-file ignores for FastAPI `Depends()`, SQLAlchemy forward refs, print in scripts/tests, alembic auto-generated files
- **[Prettier](https://prettier.io/)** added for TypeScript/CSS formatting — config in [`frontend/.prettierrc`](../frontend/.prettierrc)
- **`eslint-config-prettier`** added to disable ESLint rules that conflict with Prettier
- New npm scripts: `format`, `format:check`, `lint:fix`
- New **Makefile targets**:
  - `make lint` — full gate (Ruff check + Ruff format check + ESLint + Prettier check)
  - `make lint-fix` — auto-fix (Ruff `--fix` + ESLint `--fix`)
  - `make format` — auto-format (Ruff format + Prettier write)
  - `make format-check` — read-only format check
- Entire codebase formatted; all checks pass clean
- Lint fixes applied: `contextlib.suppress`, `StrEnum`, `raise from None`, `any()`, variable naming, stale `noqa` directives removed

### Documentation
- [`docs/STAGING.md`](STAGING.md) smoke checklist updated for the sandbox UX
- `seed_offline.py` docstring updated to document its new CI/legacy role

## Upgrade Notes

- **Backend:** `pip install -r backend/requirements.txt` — adds `ruff`
- **Frontend:** `cd frontend && npm install` — adds `prettier` and `eslint-config-prettier`
- No database migration required — `place_id` was already on the `businesses` table; only the API response schema changed

## Breaking Changes

None. The seeded demo user flow (`make seed-offline`) still works identically. The sandbox catalog is additive.

## Full Changelog

v2.5.1...v2.6.0
