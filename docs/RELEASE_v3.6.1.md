# v3.6.1 — Agent dashboard E2E coverage and CI parity

## What's New

### Deterministic Playwright coverage for the agent/dashboard browser path
- New e2e specs cover add widget, refresh persistence, remove, duplicate,
  incompatible chart recovery, manual pin, and workspace load-error
  handling.
- All new specs run against a deterministic backend so they don't depend
  on a live LLM or external API key.

### Test-only scripted LLM provider
- New `ScriptedProvider` and `/api/test/agent/script` route, gated by
  `TESTING=true` and `LLM_PROVIDER=scripted`, lets E2E tests prime exact
  agent responses for a session.
- E2E runs no longer call a live LLM or require an `OPENAI_API_KEY`.

### Playwright CI job
- New dedicated GitHub Actions Playwright job with PostgreSQL service,
  Alembic migrations, browser caching, deterministic backend/frontend
  startup, and failure artifact upload.
- Mirrors local `make test-e2e-servers` + `make test-e2e-ui` setup.

### Local validation clarifications
- `make quick` — fast lint / unit checks.
- `make validate` / `make ci-local` — non-browser CI mirror.
- `make test-e2e-servers` + `make test-e2e-ui` — local browser E2E.

### Local E2E startup hardening
- Local E2E now uses `E2E_DATABASE_URL` and a cleared placeholder
  `OPENAI_API_KEY` instead of inheriting staging credentials from
  `backend/.env`.

## Upgrade Notes

- No database migration required.
- No environment variable changes for production; new `TESTING` /
  `LLM_PROVIDER=scripted` combination is test-only.
- The new Playwright CI job needs its first push/PR run to prove the
  hosted environment.
- Mobile Playwright, drag/drop reorder, and streaming-mid-cancel coverage
  remain deferred.

## Breaking Changes

None.

## Full Changelog

v3.6.0...v3.6.1
