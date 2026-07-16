"""Global async psycopg connection pool.

Kept intentionally simple: one lazily-created pool, opened at app startup,
closed at shutdown. Callers use `async with fetch_conn() as conn`.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

from multirag.config import get_settings
from multirag.logging import get_logger

log = get_logger(__name__)

_pool: AsyncConnectionPool | None = None


async def open_pool() -> AsyncConnectionPool:
    global _pool
    if _pool is not None:
        return _pool

    settings = get_settings()
    _pool = AsyncConnectionPool(
        conninfo=settings.database_url,
        min_size=1,
        max_size=10,
        open=False,
        kwargs={"autocommit": False},
    )
    await _pool.open()
    await _pool.wait()
    log.info("db.pool.open", database_url=settings.database_url)
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is None:
        return
    await _pool.close()
    _pool = None
    log.info("db.pool.close")


def get_pool() -> AsyncConnectionPool:
    if _pool is None:
        raise RuntimeError("db pool not initialised — call open_pool() first")
    return _pool


@asynccontextmanager
async def fetch_conn() -> AsyncIterator[AsyncConnection]:
    """Borrow a connection from the pool. Use in async with blocks."""
    pool = get_pool()
    async with pool.connection() as conn:
        yield conn
