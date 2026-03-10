.PHONY: backend frontend dev stop test lint db-reset

## Start backend server
backend:
	cd backend && python -m uvicorn app.main:app --reload --port 8000

## Start frontend dev server
frontend:
	cd frontend && npm run dev

## Start both backend and frontend concurrently
dev:
	start /B cmd /C "cd backend && python -m uvicorn app.main:app --reload --port 8000"
	cd frontend && npm run dev

## Stop running backend and frontend processes
stop:
	@echo "Stopping Python/uvicorn processes..."
	-taskkill /F /IM python.exe 2>nul || pkill -f uvicorn 2>/dev/null || true
	@echo "Stopping Node/Next.js processes..."
	-taskkill /F /IM node.exe 2>nul || pkill -f next 2>/dev/null || true
	@echo "Done."

## Run backend tests
test:
	cd backend && python -m pytest tests/ -v

## Run linters
lint:
	cd backend && python -m py_compile app/main.py
	cd frontend && npm run lint

## Reset database (drops all tables — backend will recreate on next start)
db-reset:
	docker exec -i review-insight-db psql -U postgres -d review_insight \
		-c "DROP TABLE IF EXISTS analyses, reviews, businesses, users CASCADE;"
	@echo "Tables dropped. Restart backend to recreate."
