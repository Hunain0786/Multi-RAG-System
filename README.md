# multi-rag

A FastAPI service that answers questions across **three knowledge layers** with a
single Anthropic tool-use loop:

| Layer            | Backend                              | How the agent uses it                                    |
| ---------------- | ------------------------------------ | -------------------------------------------------------- |
| Structured data  | Postgres + governed semantic layer   | `compile_metric` / `compile_composite` (no NL-to-SQL)     |
| Document search  | Pinecone (serverless, cosine)        | `search_docs` over PDFs / TXT / MD                        |
| Live external    | Placeholder (phase 2)                | future adapter tools                                     |

The design mirrors a proven LookML-style semantic layer: the LLM chooses
`(metric, dimensions, filters)` from a validated registry and the compiler emits
safe parameterised SQL — the model never writes SQL.

---

## Prerequisites

- Python 3.11+
- Docker + Docker Compose (for local Postgres)
- Node.js 18+ (only for `npx prisma db push` — the runtime uses `psycopg`)
- A Pinecone account (Serverless free tier is enough) and an API key.
- An Anthropic API key.
- An OpenAI API key (used for the embedding model,
  `text-embedding-3-large` @ 1024 dim). If you'd rather run embeddings locally
  install the optional extra: `pip install -e ".[local]"` and set
  `EMBED_PROVIDER=sentence_transformers` in `.env` (downloads
  `BAAI/bge-large-en-v1.5`, ~1.3 GB, no API key needed after that).

## First-time setup

```bash
cp .env.example .env
# Fill in ANTHROPIC_API_KEY, OPENAI_API_KEY, PINECONE_API_KEY.

make install       # pip install -e .[dev]
make up            # docker compose up postgres + prisma db push + seed + pinecone-init
make ingest        # ingest ./docs/* into Pinecone
make dev           # uvicorn on http://localhost:8000
```

Health check:

```bash
curl -s http://localhost:8000/health | jq
```

## Project layout

```
prisma/schema.prisma            e-commerce + Doc registry (Prisma-managed)
prisma/seed.py                  seeds ~500 customers, 25 products, 5k orders
docs/                           sample corpora ingested into Pinecone
src/multirag/
  main.py                       FastAPI app factory + lifespan
  config.py                     pydantic-settings (.env)
  api/                          FastAPI routes (/chat SSE, /docs, /health)
  agent/                        Anthropic tool_use loop + system prompt + tools
  semantic/                     MetricDef / DimensionDef / DomainDef + compile.py
    registry/{sales,inventory,hr,finance}.py
  rag/                          chunking, loaders, embedder, Pinecone store, pipeline
  db/                           async psycopg pool
tests/                          unit tests (registry, compile SQL, chunking, guards)
```

## Semantic-layer at a glance

Four domains, each with its own fact table and metric namespace:

| Namespace   | Fact table    | Example metrics                                                       |
| ----------- | ------------- | --------------------------------------------------------------------- |
| `sales.*`   | `orders`      | `orders_count`, `revenue_total`, `aov`, `units_sold`, `refund_rate_pct` |
| `inventory.*` | `inventory` | `stock_on_hand`, `low_stock_products`, `out_of_stock_products`         |
| `hr.*`      | `employees`   | `headcount`, `new_hires`, `avg_tenure_days`, `avg_salary`              |
| `finance.*` | `transactions` | `gross_processed`, `refunded_amount`, `failure_rate_pct`, `chargeback_rate_pct` |

Dimensions declare `required_joins` so `compile_metric` assembles the right
`LEFT JOIN`s automatically. Cross-domain queries are intentionally not
supported — use `query_postgres` (read-only guard) for the rare edge cases.

## Demo prompts

Once ingested + seeded:

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Revenue by product category in Q1 2026?"}]}'
```

The agent will emit `tool_use` for `sales.revenue_total` with
`dimensions=['product_category']` and `filters={'period':'q1_2026'}`, get rows
back, and answer.

Doc-only prompt:

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"How long is the warranty on electronics, and what does it exclude?"}]}'
```

Hybrid prompt (SQL + docs, parallel tool_use):

```bash
curl -N -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"How many refunds did we process last 90 days, and what is our refund policy for electronics?"}]}'
```

Ingesting a new doc:

```bash
curl -X POST http://localhost:8000/docs/ingest \
  -F "file=@./docs/return-policy.md" \
  -F "doc_type=policy" \
  -F "tags=returns,shipping"
```

## Testing

```bash
make test          # pytest -q (unit tests only)
make lint          # ruff check
```

The unit suite does not require Postgres or Pinecone — it only exercises the
compiler, chunker, registry validation, and the query_postgres guard. Integration
tests against a live compose stack are left as a next step.

## Extending

- **Add a metric.** Add a `MetricDef` in the appropriate `semantic/registry/*.py`
  and it becomes available to the agent as `<domain>.<name>` immediately.
- **Add a domain.** Create `semantic/registry/<new_domain>.py` exporting
  `DOMAIN: DomainDef` and import it in `semantic/registry/__init__.py`.
- **Swap embeddings.** Set `EMBED_PROVIDER` in `.env` to one of
  `sentence_transformers` (default, local), `openai`, or `voyage`. Dimension
  must match the Pinecone index — recreate the index (`make pinecone-init`
  after deleting via the Pinecone console) if you change the dim. The BGE model
  is 1024-dim by default so the shipped Pinecone config works out of the box.
- **Phase 2 (live APIs).** Add an `apis/` module + register a new Anthropic tool
  schema in `agent/tools/__init__.py`.
