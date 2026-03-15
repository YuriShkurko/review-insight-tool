# Release notes — v2.2.0

**Title:** `v2.2.0 — Outscraper SDK Removal, Competitor UX, and Reliability Fixes`

**Body (paste into GitHub Releases):**

```markdown
## What's New

### Outscraper SDK Replaced with Direct API Calls
- Removed the `outscraper` Python SDK — it had **no HTTP timeout**, causing requests to hang indefinitely when the Outscraper server was slow
- Replaced with direct **httpx** calls to the same REST endpoint (`/maps/reviews-v3`) with a **120-second timeout**
- Timeouts now return a clear 504 error instead of blocking the server
- Added `reviews_returned` success logging for easier debugging

### Competitor UX Improvements
- **Inline Fetch & Analyze** — competitors can now be prepared directly from the business dashboard without navigating away; button adapts: "Fetch & Analyze" → "Analyze" → hidden (when done)
- **Fixed false error on competitor removal** — DELETE 204 (no body) was incorrectly parsed as a JSON error, showing "Failed to remove competitor" even though removal succeeded
- **Comparison grid** — snapshot cards now use a 2-column layout so 4 cards (1 target + 3 competitors) display as a clean 2×2 grid instead of 3+1

### Delete Business
- New **DELETE /api/businesses/{id}** endpoint — cascades to reviews, analyses, and competitor links
- Delete button added to each business card on the `/businesses` page with a confirmation dialog

### Google Maps URL Parsing
- Expanded regex patterns for place ID extraction (query params, data blobs, hex CIDs, ChIJ format, percent-encoded URLs)
- Added URL normalization (unquote, fragment stripping, whitespace trimming)
- Added GET fallback for short-link resolution when HEAD doesn't redirect
- **18 new unit tests** covering supported and unsupported URL formats

### Infrastructure
- **Frontend Docker entrypoint** — added `docker-entrypoint.sh` that installs `node_modules` when the volume is empty, fixing unreliable first-start behavior
- **CRLF fix** — Dockerfile strips Windows line endings from the entrypoint script at build time

### Documentation
- Added `docs/BUG_HUNT_LOG.md` — structured log of bugs found and fixed during manual testing, with a reusable template for future entries

## Breaking Changes

None. No database schema changes. Existing data is unaffected.

## Full Changelog

v2.1.0...v2.2.0
```
