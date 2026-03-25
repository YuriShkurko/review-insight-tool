# v2.9.0 — Project-specific MCP debug server

## What's New

### MCP debug server (`review-insight-debug`)
- New `backend/debug/` package — a lightweight stdio MCP server that gives Cursor direct introspection into the running project, gated behind `DEBUG_MCP=true`
- **Never deployed** — separate from the FastAPI app, not imported by `app.main`, not included in Docker or Railway builds
- Cursor auto-connects via `.cursor/mcp.json` (machine-local, gitignored)

**8 tools exposed:**

| Tool | R/W | What it returns |
|------|-----|-----------------|
| `system_status` | read | Provider, API keys present (bool only), CORS origins, DB reachable, Railway flag, JWT expiry, whether JWT secret is still the default |
| `migration_status` | read | Current Alembic revision(s), expected head, at-head bool |
| `sandbox_catalog_summary` | read | Offline manifest: business count, scenario structure, review counts per file |
| `business_snapshot` | read | Name, place_id, type, rating, review count, analysis state, competitor names, owner email — for any business UUID |
| `user_summary` | read | Email, business count, total reviews stored — by email or user_id |
| `recent_businesses` | read | Last N businesses created (default 10, max 50) with owner and analysis state |
| `db_table_counts` | read | Row counts for users, businesses, reviews, analyses, competitor_links |
| `sandbox_reset_user` | **write** | Deletes `offline_*` businesses for a user — requires `confirm=True` AND `REVIEW_PROVIDER=offline` |

**Safety boundaries:** no secrets, no API key values, no password hashes, no raw review text ever returned. The single mutating tool has a double gate.

### Config: `.env` path now file-relative
- `app/config.py` resolves `env_file` using an absolute path derived from `__file__` instead of a relative `".env"`
- Previously, any process spawned from a different working directory (e.g. Cursor's MCP runner) silently fell back to all defaults — no keys loaded, wrong provider
- Now the correct `.env` is loaded regardless of cwd

### Database: graceful import when `DATABASE_URL` is malformed
- `app/database.py` wraps `create_engine(...)` in a try/except at module level
- A malformed or missing `DATABASE_URL` (bare hostname, empty string, Railway template literal) now emits a `UserWarning` and sets `engine = None` instead of crashing the entire module import
- DB-dependent tools and routes fail at query time with a clear message rather than exploding at startup

## Upgrade Notes

- No migrations needed
- Add `mcp>=1.26.0` to your local virtualenv: `pip install -r backend/requirements.txt`
- To connect Cursor: add the `review-insight-debug` entry to your local `.cursor/mcp.json` (see `docs/DEVELOPMENT.md`)
- The `database.py` change is backwards-compatible — on Railway with a valid `DATABASE_URL`, behaviour is identical to before

## Breaking Changes

None.

## Full Changelog

v2.8.0...v2.9.0
