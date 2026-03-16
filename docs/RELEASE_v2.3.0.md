# v2.3.0 — Offline Demo Dataset, Config Cleanup, and Docs Alignment

## What's New

### Offline Demo Mode
- New `OfflineProvider` loads reviews from bundled JSON files — no Outscraper API key needed for review fetching
- **595 real reviews** across **9 businesses** in two demo scenarios:
  - **Bar**: Lager & Ale (Rothschild TLV) vs two branches (Ra'anana, Herzliya) and Beer Garden — 100/100/100/33 reviews
  - **Retail**: Rami Levy (Ariel) vs Abu Ali Supermarket and Lala Market — 33 reviews each
- Seed script (`make seed-offline`) creates a demo user, all businesses, and competitor links in one command
- Demo user: `demo@example.com` / `demo1234`
- Enable with `REVIEW_PROVIDER=offline` in `backend/.env`
- AI analysis still requires `OPENAI_API_KEY` — without one, the app falls back to sample analysis

### Competitor UX
- **Refresh button** — competitors that have already been analyzed now show a "Refresh" button to re-fetch and re-analyze, instead of hiding the action entirely
- **Address display** — competitor rows now show the business address when available, making it easier to distinguish between branches of the same chain

### Config Cleanup
- Removed `USE_MOCK_REVIEWS` backward-compatibility logic — `REVIEW_PROVIDER` is now the sole control for selecting the review source
- The `USE_MOCK_REVIEWS` field still loads from `.env` so old config files don't break, but the value is ignored
- Cleaned up references in `.env.example`, `SPEC.md`, `BUG_HUNT.md`, and integration test fixtures

### Documentation
- Rewrote README offline demo mode section with detailed scenarios, review counts, and setup instructions
- Added dedicated **Review Providers** section to README
- Updated Quick Start with a collapsible offline demo block
- Updated Features, Tech Stack, Project Structure, Testing, and Roadmap sections
- Aligned SPEC.md with current provider architecture and removed stale limitations
- Added `.cursor/` to `.gitignore`

## Breaking Changes

None. Existing `.env` files with `USE_MOCK_REVIEWS` will still load without errors — the value is simply ignored.

## Full Changelog

v2.2.0...v2.3.0
