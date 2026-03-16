# Release notes — v2.1.0

**Title:** `v2.1.0 — Architecture Cleanup, Integration Tests, and UI/UX Polish`

**Body (paste into GitHub Releases):**

```markdown
## What's New

### Service-Layer Error Refactor
- Services no longer raise **HTTPException** directly — all domain errors are now custom exceptions in `app/errors.py`
- **BusinessNotFoundError**, **BusinessAlreadyExistsError**, **NoReviewsError**, **ExternalProviderError**, **ComparisonNotReadyError** are raised by services and translated to HTTP responses in routes
- API behavior and status codes are unchanged; this is an architectural cleanup only

### Backend Integration Tests
- **12 new integration tests** using in-memory SQLite and mock providers (no real API calls)
- Covers: full business lifecycle (create → fetch → analyze → dashboard), refresh clears stale analysis, competitor add/list/remove, duplicate and self-link protections, competitor-to-regular promotion, comparison prerequisites
- New **`make test-integration`** target; **`make test`** now runs unit tests only (integration tests excluded by default)
- Fixed 3 failing dashboard schema unit tests (missing `analysis_created_at` / `last_updated_at` fields)

### UI/UX Polish
- **Business detail page** — header card with business name, actions, and metadata strip; consistent section headings (Insights, Competitors, Comparison, Reviews); wider layout (`max-w-4xl`); clearer visual hierarchy
- **Dashboard** — accent stat card for average rating; **progress bars** on complaint and praise counts (red/green); colored bullet lists for action items (blue) and risk areas (amber)
- **Competitor section** — card-based list with **dot-indicator status badges** (Analyzed / Needs analysis / Needs reviews); dashed-border empty state; cleaner add form
- **Comparison view** — **color-coded columns**: green for strengths, red for weaknesses, blue for opportunities; improved snapshot cards with compact complaint/praise lines; "You" badge on target business
- **Consistency** — unified **rounded-xl** borders, typography, button styles, and spacing across DashboardView, InsightList, CompetitorSection, ComparisonView, ReviewList, and BusinessCard

### Documentation
- README screenshots section updated for the new UI — **7 screenshots** (login, business list, dashboard header, dashboard insights, competitors, comparison, reviews)

## Breaking Changes

None. No database or API changes. Existing clients and data are unaffected.

## Full Changelog

v2.0.0...v2.1.0
```
