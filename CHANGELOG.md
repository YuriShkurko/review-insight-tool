# Changelog

## v2.6.0 — Offline Sandbox Catalog, Ruff + Prettier Tooling

### Offline Sandbox

- New API endpoints: `GET /api/sandbox/catalog`, `POST /api/sandbox/import`, `POST /api/sandbox/reset`
- Users register/login normally, browse sample businesses from the offline manifest, and import them into their own account with one click
- Competitors can be quick-added from the same offline scenario on the business detail page
- Reviews, analysis, and comparisons remain user-triggered — no pre-built dashboard
- `POST /api/sandbox/reset` clears all imported offline businesses for the current user
- `seed_offline.py` demoted to CI/legacy; in-app sandbox is now the primary demo UX
- `DashboardResponse` now includes `place_id` for catalog matching

### Frontend

- `SandboxCatalog` component (full/compact variants) on the businesses list page
- Quick-add competitors from offline catalog on business detail page
- New TypeScript types: `CatalogBusiness`, `CatalogScenario`, `CatalogResponse`
- Auth init effect refactored to satisfy `react-hooks/set-state-in-effect`

### Tooling

- **Ruff** (lint + format) added for Python — config in `backend/pyproject.toml`
- **Prettier** added for TypeScript/CSS — config in `frontend/.prettierrc`
- `eslint-config-prettier` added to prevent ESLint/Prettier conflicts
- New npm scripts: `format`, `format:check`, `lint:fix`
- New Makefile targets: `make lint`, `make lint-fix`, `make format`, `make format-check`
- Entire codebase formatted; all checks pass clean
- Lint fixes: `contextlib.suppress`, `StrEnum`, `raise from None`, `any()`, variable naming
- Removed stale `noqa` directives from SQLAlchemy models

### Documentation

- `STAGING.md` smoke checklist updated for sandbox UX
- `seed_offline.py` docstring updated for new role

### After pull

- Backend: `pip install -r backend/requirements.txt` (adds `ruff`)
- Frontend: `cd frontend && npm install` (adds `prettier`, `eslint-config-prettier`)
