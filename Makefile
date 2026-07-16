.PHONY: help install up down logs psql prisma-push seed pinecone-init ingest dev test lint format

help:
	@echo "make install       - install python deps (uv preferred)"
	@echo "make up            - docker compose up postgres + push prisma schema + seed + pinecone-init"
	@echo "make down          - docker compose down (keeps volume)"
	@echo "make down-clean    - docker compose down -v (drops volume)"
	@echo "make prisma-push   - prisma db push"
	@echo "make seed          - populate demo e-commerce data"
	@echo "make pinecone-init - idempotently create the Pinecone index"
	@echo "make ingest        - ingest every file under ./docs into Pinecone"
	@echo "make dev           - uvicorn --reload"
	@echo "make test          - pytest"
	@echo "make lint          - ruff check"
	@echo "make format        - ruff format"

install:
	python -m pip install -e ".[dev]"

up:
	docker compose up -d postgres
	@echo "Waiting for Postgres to become healthy..."
	@until docker compose exec -T postgres pg_isready -U multirag -d multirag >/dev/null 2>&1; do sleep 1; done
	$(MAKE) prisma-push
	$(MAKE) seed
	$(MAKE) pinecone-init

down:
	docker compose down

down-clean:
	docker compose down -v

logs:
	docker compose logs -f postgres

psql:
	docker compose exec postgres psql -U multirag -d multirag

prisma-push:
	npx --yes prisma@6 db push --schema prisma/schema.prisma

seed:
	python -m prisma.seed

pinecone-init:
	python -m multirag.rag.pinecone_client

ingest:
	python -m multirag.rag.pipeline ./docs

dev:
	python -m multirag --reload

test:
	pytest -q

lint:
	ruff check src tests

format:
	ruff format src tests
