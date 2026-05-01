# v3.6.1 - Agent Dashboard E2E + CI Parity

Continuation of the v3.6.0 workspace reload and widget data-integrity work.

## What Changed

- Added deterministic Playwright coverage for the agent/dashboard browser path:
  add widget, refresh persistence, remove, duplicate, incompatible chart recovery,
  manual pin, and workspace load-error handling.
- Added the test-only `ScriptedProvider` and `/api/test/agent/script` route,
  gated by `TESTING=true` and `LLM_PROVIDER=scripted`, so E2E runs do not call
  a live LLM or require an API key.
- Added a dedicated GitHub Actions Playwright job with PostgreSQL, Alembic
  migrations, browser caching, deterministic backend/frontend startup, and
  failure artifact upload.
- Clarified local validation:
  - `make quick` for fast lint/unit checks.
  - `make validate` / `make ci-local` for the non-browser CI mirror.
  - `make test-e2e-servers` + `make test-e2e-ui` for local browser E2E.
- Hardened local E2E startup so it uses `E2E_DATABASE_URL` and a cleared
  placeholder OpenAI key instead of inheriting staging credentials from
  `backend/.env`.

## Verification

```bash
make validate
# ruff check: passed
# ruff format --check: 102 files already formatted
# eslint: passed
# prettier --check: passed
# backend unit tests: 248 passed
# backend integration tests: 46 passed
# next build: passed

cd frontend && npm run test:e2e
# 7 passed
```

## Notes

- Playwright now runs in CI, but the new GitHub-hosted job still needs its first
  push/PR run to prove the hosted environment.
- Mobile Playwright, drag/drop reorder, and streaming-mid-cancel coverage remain
  deferred.
