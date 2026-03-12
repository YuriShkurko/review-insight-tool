# Review Insight Tool — System Specification

Version: 1.1  
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
| **Provider** | A pluggable module that fetches reviews from an external source (e.g., Outscraper for Google Maps). |

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
2. Backend calls the configured review provider (Outscraper or built-in sample data)
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
| `MockProvider` | Built-in sample data | `REVIEW_PROVIDER=mock` (default) |
| `OutscraperProvider` | Google Maps via Outscraper API | `REVIEW_PROVIDER=outscraper` + `OUTSCRAPER_API_KEY` |

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
| No database migrations | Schema changes require a manual table drop and recreate |
| Token in localStorage | Not suitable for production; httpOnly cookies recommended |
| No password requirements | No minimum length or complexity enforcement |
| No delete | Businesses cannot be removed once added |
| Review refresh replaces all | No incremental update; full replace clears analysis |
| Outscraper is paid | Sample data mode is free and used by default |
| Single-user focus | No teams, roles, or shared access |

## Planned Improvements

- Competitor comparison (side-by-side insights with linked competitor businesses)
- Additional review providers (Yelp, TripAdvisor)
- Alembic migrations
- Background job processing for review fetching
- Export reports (PDF/CSV)
