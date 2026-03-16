# Review Insight Tool — System Specification

Version: 1.3  
Last updated: March 2026

## Overview

Review Insight Tool is a web application that helps small business owners understand customer feedback. Users add businesses via Google Maps links, fetch reviews, and receive AI-generated analysis with actionable recommendations tailored to their business type.

## Core Concepts

| Concept | Description |
|---------|-------------|
| **Business** | A place added by a user, identified by a Google Maps place ID. Has a type (restaurant, bar, cafe, gym, salon, hotel, clinic, retail, other). |
| **Review** | A customer review fetched from an external source. Stored with a stable `external_id` and `source` tag. |
| **Analysis** | AI-generated insights for a business's reviews. Includes summary, complaints, praise, action items, risk areas, and a recommended focus. |
| **Dashboard** | Aggregated view combining business stats and analysis results. |
| **Provider** | A pluggable module that fetches reviews. Supported: `mock` (generated), `offline` (bundled real review snapshots), `outscraper` (live Google Maps). |
| **Competitor link** | A directional link from a "target" business to another business (the competitor). Stored in `competitor_links`; competitors are normal businesses owned by the same user. |
| **Comparison** | AI-generated comparison of the target business vs linked competitors that have analysis. Includes summary, strengths, weaknesses, and opportunities. |

## User Flows

### 1. Registration

1. User navigates to `/register`
2. User enters email and password
3. Backend creates user account with hashed password
4. User is redirected to `/login`

**Expected result:** User account is created. User can log in.

### 2. Login

1. User enters email and password at `/login`
2. Backend validates credentials and returns a JWT token
3. Frontend stores token and redirects to `/businesses`

**Expected result:** User is authenticated. Token is stored for subsequent requests.

### 3. Add Business

1. User pastes a Google Maps URL and selects a business type
2. Backend extracts the place ID from the URL
3. Backend resolves the business name (from the URL path or Google Places API)
4. Business record is created and linked to the user

**Expected result:** Business appears in the user's list with name, type, and zero reviews.

**Error cases:**
- Invalid or missing place ID in URL → 400 error
- Duplicate business for this user → 409 error

### 4. Fetch Reviews

1. User clicks "Fetch Reviews" on a business detail page
2. Backend calls the configured review provider (mock, offline, or Outscraper)
3. All existing reviews for this business are **deleted**
4. All existing analysis for this business is **deleted**
5. Fetched reviews are inserted as the new review set
6. Business stats (average rating, total reviews) are recomputed

**Expected result:** Business shows fresh reviews. Old analysis is cleared. Dashboard shows "Run Analysis" prompt.

**Design decision:** Replace-on-refresh ensures there is always a single, consistent review set. No mixing of data from different fetch cycles.

### 5. Run Analysis

1. User clicks "Run Analysis" on a business detail page
2. Backend loads all reviews for the business
3. Backend builds a system prompt tailored to the business type
4. Backend calls the LLM (OpenAI GPT-4o-mini) with the review text
5. LLM response is normalized into a structured result
6. Analysis record is created (or overwritten if one already exists)

**Expected result:** Dashboard displays AI summary, recommended focus, top complaints, top praise, action items, and risk areas.

**Fallback behavior:** If no OpenAI API key is configured, the backend returns sample analysis data so the app remains functional for evaluation.

### 6. View Dashboard

1. User navigates to a business detail page
2. Frontend fetches dashboard data (business info + analysis)
3. Frontend fetches review list

**Expected result:** Dashboard shows stat cards, AI insights (if analysis has been run), and a scrollable review list.

**State handling:**

| State | Dashboard behavior |
|-------|-------------------|
| No reviews, no analysis | Blue prompt: "Fetch Reviews first" |
| Reviews exist, no analysis | Amber prompt: "Run Analysis" |
| Reviews + analysis exist | Full dashboard with all insight sections |

### 7. Competitor Comparison (V2)

1. User opens a business detail page (the "target" business) that has reviews and analysis.
2. In the **Competitors** section, user pastes a Google Maps URL (or place ID) and selects business type, then clicks "Add Competitor".
3. Backend creates the competitor as a normal business (or reuses existing) and creates a `CompetitorLink` from target to competitor. Maximum 3 competitors per target.
4. Competitor appears in the list; user can open the competitor's detail page to fetch reviews and run analysis (same flow as any business).
5. Back on the target business page, when at least one linked competitor has analysis, user clicks **Generate Comparison**.
6. Backend loads target and all competitors that have analysis, sends snapshot data to the LLM, and returns a structured comparison (summary, strengths, weaknesses, opportunities).
7. Frontend displays side-by-side snapshots and the AI-generated comparison.

**Expected result:** User sees where their business is stronger or weaker vs competitors and what opportunities to prioritize.

**Constraints:** Competitors are manual only (no auto-discovery). Comparison is generated on demand, not cached. A business cannot be linked as its own competitor.

## Analysis Output Shape

Each analysis produces the following fields:

| Field | Type | Description |
|-------|------|-------------|
| `summary` | string | 2-3 sentence consultant-style assessment |
| `top_complaints` | list of `{label, count}` | Up to 5 common negative themes |
| `top_praise` | list of `{label, count}` | Up to 5 common positive themes |
| `action_items` | list of strings | Up to 5 actionable improvement suggestions |
| `risk_areas` | list of strings | Up to 3 recurring problems that need attention |
| `recommended_focus` | string | Single sentence: the #1 priority for management |

## Business Type Prompting

Analysis prompts are tailored per business type. Each type has specific focus areas:

| Type | Example focus areas |
|------|-------------------|
| Restaurant | food quality, service speed, wait times, atmosphere, value |
| Bar | drink quality, atmosphere, music/noise, pricing |
| Cafe | coffee quality, workspace suitability, service speed |
| Gym | equipment quality, cleanliness, crowding, trainers |
| Salon | scheduling, result quality, professionalism, pricing |
| Hotel | room comfort, front desk service, amenities, noise |
| Clinic | wait times, doctor communication, scheduling, billing |
| Retail | staff helpfulness, product availability, checkout speed |

The `other` type uses a generic prompt covering all standard customer experience dimensions.

## Review Provider Architecture

Providers are pluggable modules under `backend/app/providers/`. Each provider implements a `ReviewProvider` interface:

```
fetch_reviews(place_id, google_maps_url?) → list[NormalizedReview]
```

| Provider | Source | Configuration |
|----------|--------|--------------|
| `MockProvider` | Generated sample reviews seeded by place ID | `REVIEW_PROVIDER=mock` (default) |
| `OfflineProvider` | Bundled real review snapshots from `backend/data/offline/` | `REVIEW_PROVIDER=offline` |
| `OutscraperProvider` | Live Google Maps reviews via Outscraper REST API | `REVIEW_PROVIDER=outscraper` + `OUTSCRAPER_API_KEY` |

The offline provider reads from a manifest (`manifest.json`) that maps place IDs to JSON review files. A seed script (`scripts/seed_offline.py`) populates the database with demo businesses and competitor links matching the manifest.

Adding a new provider requires: creating a provider class, normalizing output to `NormalizedReview`, and registering it in the factory.

## Authentication

- JWT-based bearer token authentication
- Passwords hashed with bcrypt
- Token expiry: 24 hours (configurable)
- All business/review/analysis endpoints are user-scoped

## Data Ownership

Every business belongs to exactly one user. All queries are filtered by `user_id` to enforce ownership:

- Users can only see and interact with their own businesses
- Review and analysis operations check business ownership before proceeding

## Known Limitations

| Limitation | Notes |
|------------|-------|
| No database migrations | Schema changes require a manual table drop and recreate (V2 adds `competitor_links`; reset required when upgrading from pre-V2). |
| Token in localStorage | Not suitable for production; httpOnly cookies recommended |
| No password requirements | No minimum length or complexity enforcement |
| No incremental delete | Deleting a business cascades to all its reviews, analyses, and competitor links |
| Review refresh replaces all | No incremental update; full replace clears analysis |
| Outscraper is paid | Sample data mode is free and used by default |
| Single-user focus | No teams, roles, or shared access |

## Real Scenario Testing

### Prerequisites

Set the following in `backend/.env` for real-provider testing:

```
REVIEW_PROVIDER=outscraper
OUTSCRAPER_API_KEY=<your key>
OPENAI_API_KEY=<your key>
OUTSCRAPER_REVIEWS_LIMIT=100
OUTSCRAPER_SORT=newest
OUTSCRAPER_CUTOFF=
```

Restart the backend after changing `.env`.

**Outscraper query controls (for repeatable testing):**

| Variable | Default | Effect |
|----------|---------|--------|
| `OUTSCRAPER_SORT` | `newest` | Order: `most_relevant`, `newest`, `highest_rating`, `lowest_rating` |
| `OUTSCRAPER_CUTOFF` | (empty) | Unix timestamp: only fetch reviews **newer than** this (leave empty to fetch all) |

**Note:** The Outscraper API’s `start` parameter is a **timestamp**, not an offset, so “skip first N reviews” style pagination is not supported. To get only newer reviews (e.g. after a previous fetch), set `OUTSCRAPER_CUTOFF` to the Unix timestamp of the oldest review you already have.

### Workflow

Use a real business (e.g., a Google Maps link you own or can test against):

1. Register a new account
2. Add the business with its Google Maps URL and correct business type
3. Fetch reviews — verify review count and avg rating update
4. Run analysis — verify all dashboard fields populate (summary, complaints, praise, action items, risk areas, recommended focus)
5. Fetch reviews again — verify old analysis is cleared, dashboard prompts to re-run analysis
6. Run analysis again — verify dashboard re-populates with fresh insights
7. Inspect the dashboard — verify all sections render correctly

### Bug-Hunt Checklist

| Check | What to look for |
|-------|-----------------|
| Dashboard loads | All stat cards, insight sections, and review list render without errors |
| No duplicate reviews | Review count matches `total_reviews`; no repeated authors/text after refresh |
| Analysis fields valid | Summary is non-empty; complaints/praise have labels and counts; action items are actionable |
| Stale analysis cleared | After re-fetching reviews, dashboard shows "Run Analysis" prompt, not old data |
| Timeouts visible | Provider or LLM timeout produces a clear error, not a hang |
| Provider failures logged | Check backend logs for `op=outscraper_fetch success=false` on API errors |
| Truncation visible | If review count exceeds limits, logs show `truncated_to=` warning |
| Business stats correct | `avg_rating` and `total_reviews` match the actual fetched reviews |
| Refresh is idempotent | Fetching reviews twice in a row produces the same result |

### Checking logs during testing

Monitor backend logs in real time:

```bash
# Local
uvicorn app.main:app --reload --port 8000   # logs appear in terminal

# Docker
make logs
```

Key log patterns to watch:

```
op=outscraper_fetch query=... reviews_limit=100       # provider request
op=provider_fetch ... duration_ms=... success=true     # fetch timing
op=refresh_clear ... old_reviews_deleted=... old_analyses_deleted=...  # cleanup
op=llm_call ... duration_ms=... success=true           # analysis timing
op=fetch_reviews ... review_count=...                  # final count
```

### Further testing after a successful run

- **Refresh then re-analyze:** Fetch reviews again on the same business → confirm logs show `old_reviews_deleted=100` (or current count) and `old_analyses_deleted=1`, dashboard shows "Run Analysis", then run analysis and confirm insights update.
- **Different business / URL:** Add another business (e.g. different Maps URL), fetch and analyze — confirms no cross-business data leakage.
- **E2E test:** With backend running (`make up` or `make backend`), run `make test-e2e` to exercise the full flow automatically.
- **JWT warning in logs:** If you see `InsecureKeyLengthWarning` for the HMAC key, set `JWT_SECRET_KEY` in `.env` to a string of 32+ characters to silence it and improve security.

## Planned Improvements

- Additional review providers (Yelp, TripAdvisor)
- Alembic migrations for safe schema evolution
- Background job processing for review fetching
- Export reports (PDF/CSV)
- CI/CD pipeline (offline dataset supports this)
