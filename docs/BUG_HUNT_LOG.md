# Bug Hunt Log

Personal log of bug hunts and fixes for Review Insight Tool. Use this for your own reference; you can copy sections to Google Docs or keep it here.

**Git:** Commit this file if you want the history in the repo (e.g. private GitHub). To keep it local-only, add `docs/BUG_HUNT_LOG.md` to `.gitignore`.

---

## 2026-03-15 — Outscraper fetch hang / 504, 0 reviews

### Symptoms

- Fetch reviews: request hung with no response; UI stayed "Fetching..." indefinitely.
- Sometimes: 504 after ~300 seconds, 0 reviews returned.
- Outscraper dashboard showed the same API calls completing successfully with 33 reviews.
- Affected both a business added via short link and a previously working business (Lager & Ale).

### Investigation

- **Manual curl (PowerShell):** Direct GET to `https://api.app.outscraper.com/maps/reviews-v3?query=ChIJ...&reviewsLimit=3&async=false&sort=newest` with `X-API-KEY` returned 3 reviews in ~16 seconds → API itself works.
- **SDK inspection:** Outscraper Python SDK (`outscraper>=6.0.0`) uses `requests.request()` in its transport with **no timeout**. For sync mode it sends `async=False` and waits for the response; if the server is slow or returns late, the call blocks forever.
- **Context:** Our provider called the SDK from a sync FastAPI route (thread pool). One hanging request could block a worker; subsequent requests could queue and eventually hit a 300s timeout elsewhere (e.g. proxy/gateway) and surface as 504.

### Root cause

Outscraper SDK has no HTTP timeout and blocks indefinitely when the server is slow, so our app appeared stuck and never received the response that Outscraper had already completed (visible on their dashboard).

### Fix

- Replaced the Outscraper SDK with direct **httpx** calls to the same REST endpoint (`/maps/reviews-v3`).
- Set a **120-second timeout** so no single fetch can block longer.
- Mapped timeouts → 504 with a clear message; HTTP errors → 502.
- Removed `outscraper` from `requirements.txt`; kept `httpx` (already present).

### Files changed

| File | Change |
|------|--------|
| `backend/app/providers/outscraper_provider.py` | Use `httpx.Client(timeout=120)` and manual GET; handle `TimeoutException` and `HTTPStatusError`. |
| `backend/requirements.txt` | Removed `outscraper>=6.0.0`. |

### Outcome

- Backend builds and starts without the SDK.
- Fetch either completes within 2 minutes or fails with a clear timeout/error instead of hanging.

**Note (mystery Outscraper requests):** If you see requests on the Outscraper dashboard that you didn’t trigger, they are likely from the old SDK behaviour: our app sent the request and waited with no timeout; Outscraper processed it and showed it as completed on their side. Duplicates can be from retries or clicking Fetch multiple times while it was stuck. With the new direct httpx call and 120s timeout, new requests should match what you do.

---

## 2026-03-15 — Frontend container slow start then fail

### Symptoms

- Frontend container took ~2 min to start, then failed.
- No obvious error without checking logs.

### Root cause

Compose mounts `./frontend:/app` so you get live reload, and uses an anonymous volume for `/app/node_modules`. On first run (or after the volume is recreated), that volume is **empty**, so the container has no `node_modules` even though the image built them. `npm run dev` then fails after Next/Node tries to load (hence the delay).

### Fix

- Added `frontend/docker-entrypoint.sh`: if `node_modules` is missing, run `npm install` before `npm run dev`.
- Dockerfile: copy entrypoint to `/docker-entrypoint.sh` (so the mount doesn’t hide it), set executable, use as `ENTRYPOINT`.

### Files changed

| File | Change |
|------|--------|
| `frontend/docker-entrypoint.sh` | New: install deps when node_modules missing, then `npm run dev`. |
| `frontend/Dockerfile` | Use entrypoint instead of plain `CMD ["npm", "run", "dev"]`. |

### Outcome

- First start may take 1–2 min while `npm install` runs and fills the volume; later starts are fast.
- Rebuild frontend image after adding the entrypoint: `docker compose build frontend` then `docker compose up -d`.

---

## 2026-03-15 — Frontend container: exec entrypoint "no such file or directory"

### Symptoms

- Frontend container started then exited with code 1.
- Logs: `exec /docker-entrypoint.sh: no such file or directory`.
- localhost:3000 did not load; no frontend requests in logs.

### Root cause

`docker-entrypoint.sh` was created or edited on Windows and saved with **CRLF** line endings. Linux inside the container interprets the script with `\r` in the shebang line, so the interpreter path is not found (`/bin/sh\r` etc.), and exec fails.

### Fix

- In the Dockerfile, after copying the entrypoint, run `sed -i 's/\r$//' /docker-entrypoint.sh` before `chmod +x`, so CRLF is stripped at build time.

### Files changed

| File | Change |
|------|--------|
| `frontend/Dockerfile` | Add `RUN sed -i 's/\r$//' /docker-entrypoint.sh` before chmod. |

### Outcome

- Frontend container runs and Next.js dev server starts; localhost:3000 loads.

---

## 2026-03-15 — Remove competitor showed "Failed to remove competitor" but removal succeeded

### Symptoms

- User clicked Remove on a competitor; UI showed "Failed to remove competitor".
- Second click showed something like "Competitor not found" (or similar).
- After refreshing the page, the competitor was gone — the removal had actually succeeded.

### Root cause

Backend `DELETE /businesses/{id}/competitors/{competitor_id}` returns **204 No Content** (no response body). The frontend `apiFetch()` always called `res.json()` on success. Parsing an empty 204 body as JSON throws, so the promise rejected and the catch block showed "Failed to remove competitor." The delete had already completed on the server.

### Fix

- In `api.ts`: if `res.status === 204`, return `undefined as T` and skip `res.json()`.

### Files changed

| File | Change |
|------|--------|
| `frontend/src/lib/api.ts` | After `if (!res.ok)` block, add `if (res.status === 204) return undefined as T;` before `return res.json();`. |

### Outcome

- Remove competitor no longer shows a false error; list updates correctly after removal.

---

## Environment / infra (not code bugs)

- **Docker "Error response from daemon: i/o timeout"** when running `make up`: happens on Windows/Docker Desktop when creating or starting containers. Build often succeeds; the failure is when starting the container. **Workaround:** run `make up` again, or restart Docker Desktop. No application code change.

---

## Template for future entries

Copy the block below when adding a new bug hunt.

```markdown
## YYYY-MM-DD — Short title

### Symptoms
- What the user saw (UI, errors, logs).

### Investigation
- What you tried (curl, logs, code inspection).
- What pointed to the cause.

### Root cause
- One-line summary.

### Fix
- What was changed (code/config/docs).

### Files changed
| File | Change |
|------|--------|
| path | description |

### Outcome
- How to verify; any follow-up.
```
