.PHONY: up down logs test test-e2e lint backend frontend dev stop db-reset clean

# ── Docker Compose ──────────────────────────────────────────────

## Start the full stack (backend + frontend + database) via Docker Compose
up:
	docker compose up --build -d

## Stop the full stack
down:
	docker compose down

## Show logs from all containers (follow mode)
logs:
	docker compose logs -f

# ── Local development (without Docker) ─────────────────────────

## Start backend server locally
backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

## Start frontend dev server locally
frontend:
	cd frontend && npm run dev

## Start both backend and frontend locally (Windows)
dev:
	start /B cmd /C "cd backend && python -m uvicorn app.main:app --reload --port 8000"
	cd frontend && npm run dev

## Stop local backend and frontend processes
stop:
	@echo Stopping Python/uvicorn processes...
	-taskkill /F /IM python.exe 2>nul || pkill -f uvicorn 2>/dev/null || true
	@echo Stopping Node/Next.js processes...
	-taskkill /F /IM node.exe 2>nul || pkill -f next 2>/dev/null || true
	@echo Done.

# ── Testing & quality ──────────────────────────────────────────

## Run backend unit tests
test:
	cd backend && python -m pytest tests/ -v --ignore=tests/e2e

## Run end-to-end tests (requires running backend via make up)
test-e2e:
	cd backend && python -m pytest tests/e2e/ -v

## Run linters
lint:
	cd backend && python -m py_compile app/main.py
	cd frontend && npm run lint

# ── Database ───────────────────────────────────────────────────

## Reset database (drops all tables — backend will recreate on next start)
db-reset:
	docker exec -i review-insight-db psql -U postgres -d review_insight \
		-c "DROP TABLE IF EXISTS analyses, reviews, businesses, users CASCADE;"
	@echo Tables dropped. Restart backend to recreate.

# ── Cleanup ────────────────────────────────────────────────────

## Remove local build artifacts and caches
clean:
	-rmdir /S /Q backend\__pycache__ 2>nul || rm -rf backend/__pycache__
	-rmdir /S /Q backend\.pytest_cache 2>nul || rm -rf backend/.pytest_cache
	-rmdir /S /Q frontend\.next 2>nul || rm -rf frontend/.next
	@echo Cleaned.
