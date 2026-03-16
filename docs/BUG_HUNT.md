# Pre-V2 Acceptance Test & Bug Hunt

Short real-product validation pass before adding new features.
Run against the live system with real API keys to confirm the core workflow is solid.

## Setup

```
REVIEW_PROVIDER=outscraper
OUTSCRAPER_API_KEY=<your key>
OPENAI_API_KEY=<your key>
OUTSCRAPER_REVIEWS_LIMIT=100
OUTSCRAPER_SORT=newest
```

Start the stack (`make up` or `make dev`) and open http://localhost:3000.

Keep a terminal visible for backend logs (`make logs` or the backend terminal).

---

## Scenario 1 — Lager & Ale (full lifecycle)

| Step | Action | What to look for |
|------|--------|-----------------|
| 1 | Register a new account | Redirects to business list, no errors |
| 2 | Log out and log back in | Token works, business list loads |
| 3 | Add business — paste Lager & Ale Google Maps URL, type = **bar** | Business card appears with name, address, type badge |
| 4 | Open business detail page | Shows business name, address, "Fetch Reviews" button |
| 5 | Fetch 100 newest reviews | Review list populates, stat cards update (avg rating, total reviews), success message shows count |
| 6 | Check metadata strip | Shows "100 reviews stored" and "Last updated" timestamp |
| 7 | Run analysis | AI summary, complaints, praise, action items, risk areas, recommended focus all populate |
| 8 | Check metadata strip again | Shows "Analysis ran [timestamp]" |
| 9 | Read AI summary and insights | Content is relevant to a bar (beer, service, atmosphere, etc.), not generic filler |
| 10 | Refresh reviews (fetch again) | Success message says analysis was cleared, review count stays ~100 |
| 11 | Check dashboard | Analysis sections gone, "Run Analysis" prompt shown, metadata strip shows updated timestamp |
| 12 | Check logs | `old_reviews_deleted=100`, `old_analyses_deleted=1` visible |
| 13 | Run analysis again | Dashboard re-populates with fresh insights |
| 14 | Compare with previous analysis | Results may differ slightly (expected), but should cover similar themes |

## Scenario 2 — Second business (cross-business isolation)

Pick a different real business (restaurant, cafe, gym, etc.).

| Step | Action | What to look for |
|------|--------|-----------------|
| 1 | Add business — paste Google Maps URL, select correct type | Business card appears in list alongside Lager & Ale |
| 2 | Fetch reviews | Reviews load, count is independent from Scenario 1 |
| 3 | Run analysis | Insights are specific to this business type, not bleed-over from Lager & Ale |
| 4 | Go back to Lager & Ale | Its dashboard is unchanged — no cross-contamination |

---

## Verification checklist

### Product checks

- [ ] Dashboard wording makes sense for a non-technical user
- [ ] Business type badge displays correctly
- [ ] Metadata strip (review count, analysis timestamp, last updated) is accurate
- [ ] Workflow guidance messages appear at the right times
- [ ] "Refresh Reviews" label replaces "Fetch Reviews" after first fetch
- [ ] "Re-run Analysis" label replaces "Run Analysis" after first analysis
- [ ] Action buttons disable during loading
- [ ] Error messages are user-friendly (not raw stack traces)

### Data checks

- [ ] Review count matches `total_reviews` stat card
- [ ] No duplicate reviews (same author + same text)
- [ ] `avg_rating` is reasonable (matches Google Maps page roughly)
- [ ] Analysis fields are all populated (summary, complaints, praise, action items, risk areas, focus)
- [ ] Complaints and praise have labels and counts > 0
- [ ] Action items are actionable sentences, not placeholders
- [ ] Stale analysis is fully cleared after review refresh (no leftover data)

### System checks

- [ ] No warnings or errors in backend logs (except expected JWT key length warning if using short key)
- [ ] Outscraper fetch log shows `reviews_limit=100 sort=newest`
- [ ] Provider fetch duration logged (`duration_ms=...`)
- [ ] LLM call duration logged (`duration_ms=...`)
- [ ] Refresh clear logged (`old_reviews_deleted=... old_analyses_deleted=...`)
- [ ] No request hangs beyond 2 minutes
- [ ] Dashboard API response time under 500ms (check `op=dashboard duration_ms=...`)

---

## Findings log

Copy this table for each finding:

| Field | Value |
|-------|-------|
| **Scenario** | 1 / 2 |
| **Step** | e.g. "Step 7 — Run analysis" |
| **Expected** | What should happen |
| **Actual** | What happened |
| **Severity** | blocker / bug / minor / cosmetic |
| **Category** | product / data / system |
| **Screenshot** | (optional) |
| **Notes / next action** | Fix now / defer / investigate |

---

## After the bug hunt

- Fix any blockers or bugs before starting V2 work
- Minor / cosmetic issues can be logged as TODOs and addressed later
- If all checks pass, the system is ready for the next feature milestone
