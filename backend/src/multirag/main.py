"""FastAPI app factory + lifespan (opens DB pool, warms Pinecone handle)."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# psycopg's async client requires the selector event loop on Windows.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from multirag.api.routes import chat as chat_route
from multirag.api.routes import conversations as conversations_route
from multirag.api.routes import docs as docs_route
from multirag.api.routes import health as health_route
from multirag.api.routes import insights as insights_route
from multirag.api.routes import memory as memory_route
from multirag.config import get_settings
from multirag.db.pool import close_pool, open_pool
from multirag.logging import configure_logging, get_logger
from multirag.rag.pinecone_client import ensure_index

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    configure_logging()
    settings = get_settings()
    log.info("startup", app_env=settings.app_env, pinecone_index=settings.pinecone_index)

    await open_pool()
    try:
        ensure_index()  # idempotent
    except Exception as e:  # noqa: BLE001 — surface degraded state via /health
        log.warning("pinecone.ensure_index.failed", error=str(e))

    try:
        yield
    finally:
        await close_pool()
        log.info("shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="multi-rag",
        version="0.1.0",
        description="Multi-source RAG: SQL semantic layer + Pinecone doc search + Anthropic tool_use.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health_route.router)
    app.include_router(chat_route.router)
    app.include_router(docs_route.router)
    app.include_router(conversations_route.router)
    app.include_router(memory_route.router)
    app.include_router(insights_route.router)
    return app


app = create_app()
