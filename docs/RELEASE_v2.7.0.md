# v2.7.0 — Dashboard UX overhaul, analyze-all flow, and live feedback

## What's New

### Dashboard visual hierarchy (Laws of UX)
- **Rating as hero metric** — 5xl bold text with color coding (green ≥4.0, amber ≥3.0, red below) in a gradient card; the most important number is now the biggest on screen
- **#1 Priority card** — Recommended Focus promoted to the hero row with a bold border and label; impossible to miss
- **Reviews + Insights** grouped as smaller secondary stat cards next to the hero rating
- **AI Summary** — full-width with larger text and more spacing for readability
- **Action Items & Risk Areas** at the bottom where users expect lower-priority detail

### Analyze All & Compare
- Single **"Analyze All & Compare"** button: fetches reviews and runs analysis on all unready competitors, then auto-generates the comparison
- Re-analyzing a single competitor via "Refresh" also auto-triggers comparison regeneration
- Secondary **"Compare Ready Only"** button when some but not all competitors are ready
- **Comparison prerequisites checklist** with ✓/○/◐ status for your business and competitors

### Live feedback
- **Pulsing animation** on all action buttons while busy (fetch, analyze, compare, competitor prepare) — the UI never looks dead during long operations
- **Toast notifications** — green success toast on fetch/analyze/compare completion; auto-dismisses after 4 seconds with fade animation
- Removed inline success banners in favor of toasts to reduce visual clutter

### Clickable review count
- "X reviews stored" in the header metadata smooth-scrolls to the reviews section
- "Reviews" stat card in the dashboard smooth-scrolls to reviews when clicked

### Collapsible sections
- Insights, Competitors, Comparison, and Reviews sections are collapsible with a triangle toggle
- All sections default to open

### Competitor status badges
- Show **"No reviews"** / **"Needs analysis"** / **"Ready · Mar 23, 7:30 PM"** with analysis timestamp
- Backend `CompetitorRead` now includes `analysis_created_at`

## Upgrade Notes

- Backend: `CompetitorRead` schema adds optional `analysis_created_at` field — backward compatible, no migration needed
- Frontend: new `Toast.tsx` component; `globals.css` adds `animate-pulse-slow` keyframes

## Breaking Changes

None.

## Full Changelog

v2.6.0...v2.7.0
