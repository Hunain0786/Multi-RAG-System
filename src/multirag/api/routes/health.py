"""Liveness + readiness endpoints."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from multirag.db.pool import fetch_conn
from multirag.rag.pinecone_client import get_index

router = APIRouter(prefix="", tags=["health"])


@router.get("/health")
async def health() -> dict[str, Any]:
    postgres_ok = False
    pinecone_ok = False
    pinecone_stats: dict[str, Any] = {}

    try:
        async with fetch_conn() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1;")
                postgres_ok = True
    except Exception as e:  # noqa: BLE001
        postgres_ok = False
        pinecone_stats["postgres_error"] = str(e)

    try:
        stats = get_index().describe_index_stats()
        pinecone_stats["namespaces"] = list((stats.get("namespaces", {}) or {}).keys())
        pinecone_stats["total_vector_count"] = stats.get("total_vector_count", 0)
        pinecone_ok = True
    except Exception as e:  # noqa: BLE001
        pinecone_ok = False
        pinecone_stats["pinecone_error"] = str(e)

    return {
        "status": "ok" if postgres_ok and pinecone_ok else "degraded",
        "postgres": postgres_ok,
        "pinecone": pinecone_ok,
        "pinecone_stats": pinecone_stats,
    }
