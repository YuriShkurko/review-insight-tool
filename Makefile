.PHONY: up down logs test test-integration test-e2e lint lint-fix format format-check validate frontend-build ci-local backend frontend dev debug stop db-reset db-add-is-competitor seed-offline seed-offline-local clean db-upgrade db-upgrade-local db-downgrade db-current db-revision db-history db-stamp-head pdf aws-bootstrap aws-rds aws-network aws-alb aws-ecs aws-logs-backend aws-logs-frontend aws-status aws-teardown

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
## Backend runs in background. If you get "network error" on login, run "make backend" in another terminal to see backend logs (e.g. DB not running).
dev:
	@echo Starting backend on http://localhost:8000 ...
	cmd /C "cd /d $(CURDIR)\backend && start /B python -m uvicorn app.main:app --reload --port 8000"
	@echo Starting frontend on http://localhost:3000 ...
	cd frontend && npm run dev

## Start the full stack in DEBUG mode — enables E2E tracing + UI element selector
## Backend: DEBUG_TRACE=true  →  X-Trace-Id headers, trace ring buffer, /api/debug/ui-snapshot
## Frontend: NEXT_PUBLIC_DEBUG_TRAIL=true  →  debug panel (bottom-left ◉), CTRL+click selector
## The review-insight-debug MCP server is auto-spawned by Claude Code via .mcp.json (stdio).
debug:
	@echo Starting backend in DEBUG mode on http://localhost:8000 ...
	cmd /C "cd /d $(CURDIR)\backend && set DEBUG_TRACE=true&& start /B python -m uvicorn app.main:app --reload --port 8000"
	@echo Starting frontend in DEBUG mode on http://localhost:3000 ...
	cmd /C "cd /d $(CURDIR)\frontend && set NEXT_PUBLIC_DEBUG_TRAIL=true&& npm run dev"

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
	cd backend && python -m pytest tests/ -v --ignore=tests/e2e --ignore=tests/integration

## Run integration tests (uses in-memory SQLite, no running server needed)
test-integration:
	cd backend && python -m pytest tests/integration/ -v

## Run end-to-end tests (requires running backend via make up)
test-e2e:
	cd backend && python -m pytest tests/e2e/ -v

## Check all linters (ruff + eslint + prettier) — fails on any violation
lint:
	@echo ── Python (ruff check) ──────────────────────────────
	cd backend && python -m ruff check .
	@echo ── Python (ruff format --check) ─────────────────────
	cd backend && python -m ruff format --check .
	@echo ── TypeScript (eslint) ──────────────────────────────
	cd frontend && npm run lint
	@echo ── TypeScript (prettier --check) ────────────────────
	cd frontend && npm run format:check
	@echo ✓ All checks passed.

## Auto-fix lint issues (ruff + eslint --fix)
lint-fix:
	@echo ── Python (ruff check --fix) ────────────────────────
	cd backend && python -m ruff check --fix .
	@echo ── TypeScript (eslint --fix) ────────────────────────
	cd frontend && npm run lint:fix
	@echo ✓ Lint fixes applied.

## Auto-format all code (ruff format + prettier)
format:
	@echo ── Python (ruff format) ─────────────────────────────
	cd backend && python -m ruff format .
	@echo ── TypeScript (prettier --write) ────────────────────
	cd frontend && npm run format
	@echo ✓ All code formatted.

## Check formatting without modifying files
format-check:
	@echo ── Python (ruff format --check) ─────────────────────
	cd backend && python -m ruff format --check .
	@echo ── TypeScript (prettier --check) ────────────────────
	cd frontend && npm run format:check
	@echo ✓ Formatting OK.

## Run the same validation as GitHub Actions (requires Python + Node deps installed locally)
## Order: lint (includes format checks) → unit tests → integration tests → frontend production build
validate: lint test test-integration frontend-build
	@echo ✓ validate complete.

## Same as validate (alias)
ci-local: validate

## Frontend production build (set NEXT_PUBLIC_API_URL in frontend/.env.local if needed)
frontend-build:
	cd frontend && npm run build

# ── Database ───────────────────────────────────────────────────

## Apply all pending Alembic migrations (run after `make up`)
db-upgrade:
	docker compose exec backend alembic upgrade head

## Apply migrations using local `alembic` (uses `backend/.env` DATABASE_URL; Postgres must be reachable)
db-upgrade-local:
	cd backend && alembic upgrade head

## Roll back one migration revision
db-downgrade:
	docker compose exec backend alembic downgrade -1

## Show current Alembic revision
db-current:
	docker compose exec backend alembic current

## Create a new autogenerated migration (usage: make db-revision msg="add column foo")
db-revision:
	docker compose exec backend alembic revision --autogenerate -m "$(msg)"

## Show migration history
db-history:
	docker compose exec backend alembic history --verbose

## Stamp DB as up-to-date without running migrations (one-time: existing DB from create_all era)
## Example: docker compose exec backend alembic stamp head
db-stamp-head:
	docker compose exec backend alembic stamp head

## Reset database (drops all tables and Alembic version — use only as escape hatch)
## After reset, run: make db-upgrade
## For standalone DB container (review-insight-db), run: docker exec -i review-insight-db psql -U postgres -d review_insight -c "DROP TABLE IF EXISTS alembic_version, competitor_links, analyses, reviews, businesses, users CASCADE;"
db-reset:
	docker compose exec -T db psql -U postgres -d review_insight \
		-c "DROP TABLE IF EXISTS alembic_version, competitor_links, analyses, reviews, businesses, users CASCADE;"
	@echo Tables dropped. Run: make db-upgrade

## Add is_competitor column to existing DB (legacy escape hatch; prefer migrations)
db-add-is-competitor:
	docker compose exec -T db psql -U postgres -d review_insight \
		-c "ALTER TABLE businesses ADD COLUMN IF NOT EXISTS is_competitor boolean NOT NULL DEFAULT false;"
	@echo Column added. Restart backend if needed.

# ── Offline demo data ─────────────────────────────────────────

## Seed database with offline demo businesses and competitor links
seed-offline:
	docker compose exec backend python -m scripts.seed_offline

## Same as seed-offline but runs local Python (requires schema from migrations; DB from backend/.env)
seed-offline-local:
	cd backend && python -m scripts.seed_offline

# ── Cleanup ────────────────────────────────────────────────────

## Remove local build artifacts and caches
clean:
	-rmdir /S /Q backend\__pycache__ 2>nul || rm -rf backend/__pycache__
	-rmdir /S /Q backend\.pytest_cache 2>nul || rm -rf backend/.pytest_cache
	-rmdir /S /Q frontend\.next 2>nul || rm -rf frontend/.next
	@echo Cleaned.


# ── Docs ────────────────────────────────────────────────────────
## Regenerate INTERVIEW_PREP.pdf (Mermaid diagrams pre-rendered via system Chrome)
pdf:
	node scripts/build-pdf.mjs

# ── AWS Deployment ─────────────────────────────────────────────

## Step 1: Create ECR repos, IAM role, store secrets in SSM
aws-bootstrap:
	bash infrastructure/01-bootstrap.sh

## Step 2: Create RDS PostgreSQL instance (skip if using Railway DB)
aws-rds:
	bash infrastructure/02-rds.sh

## Step 3: Create security groups (uses default VPC)
aws-network:
	bash infrastructure/03-network.sh

## Step 4: Create Application Load Balancer + routing rules
aws-alb:
	bash infrastructure/04-alb.sh

## Step 5: Create ECS cluster, task definitions, and services
aws-ecs:
	bash infrastructure/05-ecs.sh

## Stream backend logs from ECS (CloudWatch)
aws-logs-backend:
	aws logs tail /ecs/review-insight-backend --follow --region $(or $(AWS_REGION),eu-central-1)

## Stream frontend logs from ECS (CloudWatch)
aws-logs-frontend:
	aws logs tail /ecs/review-insight-frontend --follow --region $(or $(AWS_REGION),eu-central-1)

## Show ECS service health (running/desired counts)
aws-status:
	aws ecs describe-services \
		--cluster review-insight \
		--services review-insight-backend review-insight-frontend \
		--region $(or $(AWS_REGION),eu-central-1) \
		--query 'services[*].{name:serviceName,running:runningCount,desired:desiredCount,status:status}' \
		--output table

## Delete all AWS resources (stops billing — use with care)
aws-teardown:
	bash infrastructure/teardown.sh
