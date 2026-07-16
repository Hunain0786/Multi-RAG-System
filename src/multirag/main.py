"""FastAPI app factory + lifespan (opens DB pool, warms Pinecone handle)."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from multirag.api.routes import chat as chat_route
from multirag.api.routes import docs as docs_route
from multirag.api.routes import health as health_route
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
    ensure_index()  # idempotent — safe on every boot

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
    return app


app = create_app()
