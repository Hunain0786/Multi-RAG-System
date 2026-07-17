.PHONY: help install up down logs seed ingest dev dev-backend dev-frontend test lint format frontend-install frontend-build

help:
	@echo "Backend (delegates to backend/Makefile):"
	@echo "  make install         - pip install -e '.[dev]' in backend/"
	@echo "  make up              - docker compose up postgres + prisma push + seed + pinecone-init"
	@echo "  make down            - docker compose down (keeps volume)"
	@echo "  make seed            - populate demo e-commerce data"
	@echo "  make ingest          - ingest backend/docs/* into Pinecone"
	@echo "  make dev-backend     - uvicorn --reload on :8000"
	@echo "  make test            - pytest -q"
	@echo "  make lint            - ruff check"
	@echo ""
	@echo "Frontend:"
	@echo "  make frontend-install - npm install in frontend/"
	@echo "  make dev-frontend     - next dev on :3000"
	@echo "  make frontend-build   - next build"
	@echo ""
	@echo "Both:"
	@echo "  make dev             - run backend + frontend in parallel"

install:
	$(MAKE) -C backend install

up:
	$(MAKE) -C backend up

down:
	$(MAKE) -C backend down

logs:
	$(MAKE) -C backend logs

seed:
	$(MAKE) -C backend seed

ingest:
	$(MAKE) -C backend ingest

test:
	$(MAKE) -C backend test

lint:
	$(MAKE) -C backend lint

format:
	$(MAKE) -C backend format

dev-backend:
	$(MAKE) -C backend dev

frontend-install:
	npm --prefix frontend install

frontend-build:
	npm --prefix frontend run build

dev-frontend:
	npm --prefix frontend run dev

dev:
	$(MAKE) -j2 dev-backend dev-frontend
