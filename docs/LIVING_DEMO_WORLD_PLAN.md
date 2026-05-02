# Living Demo World — AI Traffic & “Fake Economy” Plan

> **Status:** planning only  
> **Goal:** Let an interviewer log into a **controlled demo universe** where businesses and reviews **evolve over time** (wave-like or narrative-driven), so the product feels alive—E2E, real DB, real UI—without touching production or paid Maps volume.  
> **Context tools:** Keep this artifact in **Scribe** for narrative threads; use **Locus** before implementation to map blast radius (providers, `review_service`, routes, tenancy).

---

## 1. North-star experience

**Persona:** Interviewer (or you) opens the hosted **demo** URL, signs in as a **demo tenant**, lands on a dashboard that already has **motion**: competitor counts drift, new reviews appear after refresh, maybe a “pulse” strip (“Neighborhood activity ↑ this hour”).

**Feel:** Lightweight **tycoon / idle sim** energy: the world ticks in the background; the **product remains honest** (same APIs, same refresh button)—the “magic” is **injected state**, not mocked UI chrome.

---

## 2. Hard constraints from the current codebase

| Constraint | Implication for simulation |
|------------|------------------------------|
| **Multi-tenant** | All synthetic businesses/reviews must belong to **known demo `user_id`s** (or a single `demo@…` account with many businesses). Never write into other tenants. |
| **`fetch_reviews` replaces the full set** and clears analysis | “Growing” review volume is either **append-then-replace inside one fetch** (provider returns growing list) or you **accept** that analysis drops until user re-runs (could be a **feature** in demo: “New chatter—re-analyze”). |
| **`ReviewProvider` is env-selected** (`mock` / `offline` / `outscraper`) | A fourth provider **`simulation`** (or **`living`**) is the cleanest seam: same `fetch_reviews` contract, reads from **DB or sim state** instead of static JSON. |
| **Offline provider reads static files** | Good for **deterministic reels**; bad for **continuous mutation** unless a process **rewrites** `data/offline` (possible but racy for concurrent demos). |
| **OpenAI cost / latency** | Full LLM on every synthetic tick is expensive. Prefer **batched analysis**, **cached templates**, or **deterministic text** for background churn and reserve LLM for **on-demand** “hero” moments. |
| **MAX_COMPETITORS = 3** | Narrative design: “three rivals in the neighborhood” max. |

These constraints are **non-negotiable** for a credible implementation plan; Locus should be run before refactors to see coupling (`get_review_provider`, `fetch_reviews_for_business`, routes).

---

## 3. Conceptual architecture: three layers

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER A — World orchestrator (new component)                │
│  Tick loop, schedules, wave functions, budgets, narratives   │
└───────────────┬─────────────────────────────────────────────┘
                │ writes / mutates
┌───────────────▼─────────────────────────────────────────────┐
│  LAYER B — Truth store (choose one primary)                  │
│  (1) PostgreSQL rows (Business, Review, …)                  │
│  (2) Sim state + custom ReviewProvider reading it           │
│  (3) Hybrid: PG for businesses, provider returns reviews      │
└───────────────┬─────────────────────────────────────────────┘
                │ read by
┌───────────────▼─────────────────────────────────────────────┐
│  LAYER C — Existing product (unchanged UX path)              │
│  User refresh → provider → replace reviews → UI + analysis   │
└─────────────────────────────────────────────────────────────┘
```

**Locus question to answer early:** Should the orchestrator **only** call **public HTTP APIs** (black-box, safest) or **import app services** (white-box, fewer round-trips, tighter coupling)?

---

## 4. Options for “who writes reviews” (mix and match)

| Mode | Pros | Cons |
|------|------|------|
| **A. Deterministic dataset + scripted curves** | Cheap, reproducible, interview-safe; easy to demo “sinus” rating drift. | Feels less “magical”; text repeats unless you rotate templates. |
| **B. LLM batch writer** | Rich, varied language; personas (harsh critic, fan). | Cost, rate limits, non-determinism; need guardrails and caching. |
| **C. Hybrid** | LLM generates **N templates** offline; runtime picks + parameterizes by wave (sentiment, length, star). | Best ROI for demos; one-time spend. |
| **D. Embeddings / retrieval** | Pull from a pool of real-ish snippets (licensed or synthetic). | More moving parts. |

**Recommendation for v0:** **C** — LLM or hand-authored **template bank** + runtime **parameters** (rating mean, variance, topic tags) driven by the wave engine. **B** for optional “special event” bursts (e.g. “festival weekend” dump of 5 reviews).

---

## 5. Wave engine — “sinus” is one knob among many

Not only sine waves; anything **periodic + bounded** reads well on a chart:

- **Intensity:** reviews per hour = baseline + amplitude × sin(2πt / T) — slow “seasons.”
- **Sentiment offset:** shift mean rating with a **triangle or trapezoid** wave (ramp up controversy, resolve).
- **Competitor activity:** linked competitor businesses get **offset phase** so they are not in lockstep (interviewer sees relative motion).
- **Events:** discrete spikes (PR crisis, holiday rush) on top of smooth waves—**Fourier-lite** storytelling.

**Storage for wave state:** small table or JSON blob keyed by `demo_universe_id` (`phase`, `period_sec`, `amplitudes`, `last_tick_at`) so restarts are deterministic if seeded.

---

## 6. AI “agents” (logical roles, not necessarily separate processes)

| Agent | Responsibility |
|-------|------------------|
| **Registrar** | Creates businesses with valid `place_id` / URLs consistent with provider (for `simulation`: synthetic ids in a reserved namespace `sim_…`). |
| **Linker** | Maintains competitor graph under MAX_COMPETITORS rules; occasional “new rival appears” event. |
| **Chronicler** | Appends or regenerates review payloads the provider will return on next fetch. |
| **Analyst (optional)** | Pre-computes analysis JSON for demo speed, or triggers real `analyze` sparingly. |
| **Director** | Chooses narrative arc (calm week → storm → recovery); maps to wave parameters. |

**Implementation sketch:** one **Python worker** (Celery later; for demo **asyncio loop** or **cron**) with pluggable “behaviors.”

---

## 7. Integration strategies (pick one MVP)

### Strategy 1 — **`SimulationProvider` (recommended MVP seam)**

- Add `REVIEW_PROVIDER=simulation`.
- Provider reads **Postgres** (or Redis) table `sim_reviews` / materialized view keyed by `business.place_id`.
- Orchestrator **INSERT/UPSERT** rows between ticks; user hits **Refresh** → sees new world.
- **Pros:** Zero change to FastAPI route contract; demo is “real.” **Cons:** Need migration + seed cleanup.

### Strategy 2 — **HTTP-only bot (black box)**

- Reuse synthetic monitor pattern: register, create businesses, call fetch/analyze on a schedule **as real users**.
- **Pros:** No provider change. **Cons:** Heavy; still need believable Maps URLs / mock provider; harder to get smooth “wave” without many API calls.

### Strategy 3 — **Mutating offline catalog**

- Cron rewrites `backend/data/offline` JSON + manifest; `REVIEW_PROVIDER=offline`.
- **Pros:** No DB writes for reviews. **Cons:** File locking, git churn if committed, awkward for multi-demo concurrency.

### Strategy 4 — **Frontend-only illusion**

- Fake counters in demo build.  
- **Reject** for your stated goal (“real system E2E”).

**MVP path:** **Strategy 1** + deterministic templates; **Strategy 2** as optional “soak test” reuse.

---

## 8. Demo safety & ops

- **Dedicated demo deployment** (Railway or ECS with `DEPLOY_ENV=demo`), separate DB, **nightly reset** or **TTL job** (truncate `sim_%` businesses).
- **Feature flag** `DEMO_WORLD_ENABLED` on orchestrator only.
- **Cost ceiling:** max OpenAI calls per hour; circuit breaker to deterministic text.
- **Scribe:** track open decisions (provider name, reset policy, LLM budget). **Locus:** before touching `providers/` or `review_service.py`, run impact on tests and CI env (`REVIEW_PROVIDER=mock` unchanged).

---

## 9. Interviewer Telegram concierge

**Reuse:** The same Telegram bot and credentials already planned for **Grafana → Telegram alerts** in `docs/OBSERVABILITY_PLAN.md` can double as a **human-facing concierge** for demo provisioning, as long as you separate **routing** (e.g. different chat commands vs alert message format) and avoid mixing on-call panic traffic with “spin up demo” chatter—or use a second bot token if you want a hard split later.

**Interviewer flow (concept):**

1. Interviewer sends a short command to the bot (e.g. `/demo` or `start demo`), optionally with a **window** (“1 hour”) or **profile** (“busy cafe”).
2. Bot replies immediately with an **honest ETA** assembled from known timings: cold start of demo stack, DB seed, orchestrator warm-up, optional image pull—e.g. “About **8–12 minutes**; I’ll message you when it’s ready. You’ll have **~60 minutes** live before auto teardown.”
3. A **controller** (GitHub Action `workflow_dispatch`, small worker on your infra, or ECS task) provisions or **resumes** the demo environment, seeds the living world, flips `DEMO_WORLD_ENABLED`, and registers a **deadline** (wall clock + TTL).
4. When health checks pass (API + optional synthetic smoke), the bot sends **“Live now”** plus **credentials link** (one-time magic login or instructions to a shared demo account), **URL**, and **“Session ends at HH:MM UTC”**.
5. At **T−5 minutes** optional nudge; at **T** send “Session winding down / gone” and trigger **reset** (truncate sim data, scale to zero, or park universe to idle).

**Why it fits the “video game” pitch:** push notifications mirror “match ready” in multiplayer—low friction for someone on a phone between meetings.

**Implementation notes (planning only):**

- **ETA source of truth:** store rolling averages from past deploys (artifact in Scribe or small JSON in repo) so the bot does not lie; fallback conservative upper bound.
- **Idempotency:** duplicate `/demo` while a spin is in flight should return status “already building” with job id, not two stacks.
- **Security:** do not paste secrets in Telegram; use **short-lived magic links** or “reply with email to receive invite” if you ever need private creds.
- **Observability link:** when the demo stack is up, Grafana alerts on that environment still land on the same bot—use **prefix tags** in message text (`[ALERT]` vs `[DEMO]`) so filters stay sane.

---

## 10. Phased roadmap

| Phase | Outcome |
|-------|---------|
| **P0 — Paper** | This doc + Scribe artifact + Locus scan output linked as `documents` edge. |
| **P1 — Static living** | Seeded Postgres + `SimulationProvider` returning template reviews; manual tick script. |
| **P2 — Clock** | Background worker + sine parameters + interviewer login script. |
| **P3 — Narrative** | Director arcs + optional LLM bursts + competitor phase offsets. |
| **P4 — Show mode** | Read-only “theater” user + optional WebSocket **activity feed** (product extension; not required for core illusion). |
| **P5 — Telegram concierge** | Command → ETA → provision → “live for N min” → teardown nudge; reuse observability bot or split tokens. |

---

## 11. Open questions (for Scribe / design sessions)

1. Should **analysis** auto-run on a schedule for demo accounts, or always require button click (authentic vs. motion)?  
2. One **global** demo universe vs. **per-interviewer** isolated universe (copy-on-login)?  
3. Legal/copy: disclose “synthetic data” in UI footer for trust?  
4. Mobile vs desktop demo—any layout constraints for “pulse” UI?  
5. **Telegram:** single bot for alerts + demo concierge, or two bots? Who is allowed to trigger `/demo` (allowlist of Telegram user ids)?

---

## 12. Tagline candidates (for README or demo landing)

- “A neighborhood that runs itself—synthetic traffic, real stack.”  
- “Turn the portfolio into a living tycoon bar chart.”  

---

*Next step when you move from plan to build: run Locus `get_impact` on `app/providers/factory.py` + `review_service.py`, then open a Scribe **task** child under this **spec** with acceptance criteria for P1.*
