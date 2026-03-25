# Development automation

This repo uses **Make** for local shortcuts and **GitHub Actions** for push/PR validation. Nothing here deploys to staging or production.

## CI (GitHub Actions)

Workflow: [`.github/workflows/ci.yml`](../.github/workflows/ci.yml)

- Runs on pushes and pull requests to `main` / `master`.
- **Backend job:** `ruff check`, `ruff format --check`, unit tests, integration tests.
- **Frontend job:** `eslint`, `prettier --check`, `next build`.
- **Not included:** E2E tests (they expect a running API at `BASE_URL`), database containers, or deploy steps.

Integration tests use **in-memory SQLite** via `tests/integration/conftest.py`; CI sets `DATABASE_URL=sqlite:///:memory:` so Postgres is not required.

## Local validation (mirror CI)

After installing backend (`pip install -r requirements.txt`) and frontend (`npm ci` in `frontend/`) dependencies:

```bash
make validate
```

This runs `make lint` (Python + TS lint and format checks), `make test`, `make test-integration`, and `npm run build` in `frontend/`. For the build, ensure `frontend/.env.local` exists with `NEXT_PUBLIC_API_URL` if your setup needs it (see `frontend/.env.local.example`).

Alias: `make ci-local` (same as `validate`).

## Docker-based vs local DB commands

| Goal | Docker Compose stack running | Local Postgres + `backend/.env` |
|------|-------------------------------|----------------------------------|
| Apply migrations | `make db-upgrade` | `make db-upgrade-local` |
| Seed offline demo | `make seed-offline` | `make seed-offline-local` |

`db-upgrade-local` and `seed-offline-local` use your machine’s Python and the `DATABASE_URL` in `backend/.env` — they do **not** start Postgres for you.

## Debug event trail

A lightweight debug tool for inspecting what the user did, what API calls ran, and what state transitions occurred — useful for diagnosing frontend bugs and staging issues.

### How to enable

Add to `frontend/.env.local` (create the file from `frontend/.env.local.example` if it doesn't exist):

```
NEXT_PUBLIC_DEBUG_TRAIL=true
```

Then restart the dev server (`make frontend` or `npm run dev` in `frontend/`). The flag is **off by default** and must be set explicitly — normal users never see it. It is a `NEXT_PUBLIC_` variable, so it is baked into the client build; do not set it in production.

### What it captures (up to 200 recent events, oldest overwritten)

| Kind | When |
|------|------|
| `route:change` | Browser navigates to a new page |
| `auth:login` / `auth:logout` | User logs in or out |
| `auth:restore` / `auth:restore-fail` | Token verified or discarded on page load |
| `api:start` / `api:ok` / `api:fail` | Every `apiFetch` call — method, path, status, error detail |
| `biz:load-start` / `biz:load-ok` / `biz:load-fail` | Business detail page load attempt |
| `biz:fetch-reviews` / `biz:analyze` / `biz:compare` / `biz:analyze-all-compare` | Action buttons on business detail |
| `biz:retry` | Retry button on error screen |
| `biz:add` / `biz:delete` | Add or delete a business from the list page |
| `sandbox:import` / `sandbox:reset` | Offline sandbox actions |
| `comp:add` / `comp:remove` / `comp:quick-add` / `comp:prepare` | Competitor section actions |

Events include `ts` (timestamp), `kind`, `route` (current path), and a short `detail` object. Sensitive fields (`token`, `password`, `authorization`, `secret`) are stripped. String values in `detail` are truncated at 200 chars.

### Debug panel UI

When enabled, a small **"◉ Debug ▼"** button appears in the **bottom-left corner** of the app. Click it to open the event panel:

- **Event list** — most recent at top; each row shows kind, time-ago, route, and detail summary. Auto-refreshes every 2 seconds while open.
- **Copy** — copies the full JSON dump to the clipboard.
- **↓ Save** — downloads `debug-trail-{timestamp}.json`.
- **Clear** — resets the buffer.

### What bugs this helps diagnose

- **Missing-business / 404 / retry:** see `biz:load-fail` with status + detail, followed by `biz:retry`.
- **Stale state after navigation:** `route:change` events show when navigation happened vs. when `biz:load-ok` fired — late responses show up as out-of-order events.
- **Sandbox import failures:** `sandbox:import` → `api:fail` sequence shows exactly what the API returned.
- **Auth session expiry:** `auth:restore-fail` at startup means the stored token was rejected.
- **Competitor prepare failures:** `comp:prepare` → `api:fail` pinpoints which competitor + what error.

### Staging / Railway usage

On Railway, build the frontend with `NEXT_PUBLIC_DEBUG_TRAIL=true` in the service's environment variables to get the panel in staging. **Remove it before switching to production traffic** (or keep a separate staging service env).

## MCP debug server

A project-specific backend introspection server for local debugging and staging triage. Not a product feature — never deployed to Railway.

### What it is

A small [MCP](https://modelcontextprotocol.io) server (`backend/debug/`) that Cursor connects to over stdio. It exposes 8 tools for inspecting the live database, config, Alembic state, and sandbox catalog — all reusing the existing app models and config, with no new infrastructure.

It is **not** part of the FastAPI app. It runs as a separate local process and is ignored by Docker and Railway.

### How to start it

```bash
cd backend/
DEBUG_MCP=true python -m debug.mcp_server
```

The `DEBUG_MCP=true` flag is required. Without it the server exits immediately. Cursor connects automatically when the server is listed in `.cursor/mcp.json`.

### Tool catalog

| Tool | R/W | What it returns |
|------|-----|-----------------|
| `system_status` | read | `REVIEW_PROVIDER`, API keys present (bool only), CORS origins, DB reachable, Railway flag, JWT expiry, whether JWT secret is still the default |
| `migration_status` | read | Current Alembic revision(s), expected head, whether schema is at head |
| `sandbox_catalog_summary` | read | Offline manifest: business count, scenario structure, review counts per file |
| `business_snapshot` | read | Name, place_id, type, rating, review count, analysis state, competitor names, owner email — for any business by UUID |
| `user_summary` | read | Email, business count, total reviews stored — by email or user_id |
| `recent_businesses` | read | Last N businesses created (default 10, max 50) with owner and analysis state |
| `db_table_counts` | read | Row counts for users, businesses, reviews, analyses, competitor_links |
| `sandbox_reset_user` | **write** | Deletes `offline_*` businesses for a user. Requires `confirm=True` and `REVIEW_PROVIDER=offline` |

### Safety

Never exposed: `JWT_SECRET_KEY`, `DATABASE_URL`, any API key value, or password hashes. Raw review text is never returned.

`sandbox_reset_user` is the only mutating tool. It has two hard gates:
1. `confirm=True` must be explicitly passed
2. `REVIEW_PROVIDER` must be `"offline"`

Stdio transport only — no HTTP listener, not reachable over the network.

### Example: debugging a broken business detail page

```
You: business_snapshot(business_id="<id from URL>")
→ shows review count, has_analysis, competitor state, owner

You: system_status()
→ confirms provider, DB reachable, migration state

You: migration_status()
→ confirms schema is at head
```

### What it is NOT for

- No production use — local and staging debug only
- No log tailing or request interception
- No OpenAI prompt replay
- No review content inspection
- No changes to non-sandbox user data

## Staging / Railway

Manual deploy and env configuration are unchanged; see [STAGING.md](STAGING.md). CI does not push images or touch Railway.
