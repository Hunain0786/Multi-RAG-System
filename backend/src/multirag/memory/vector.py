"""Pinecone wrapper for the agent-memory namespace.

Doc chunks live in the default namespace and are scoped by metadata; memory
facts live in `namespace="memory"` for hard isolation. The vector id equals the
Postgres `memory_facts.id` so we can round-trip cleanly.
"""

from __future__ import annotations

import asyncio
from typing import Any

from multirag.rag.embedder import get_embedder
from multirag.rag.store import Hit, delete_ids, query as store_query, upsert as store_upsert

NAMESPACE = "memory"


async def upsert_fact_vector(
    fact_id: str,
    text: str,
    metadata: dict[str, Any],
) -> None:
    """Embed and upsert a single fact into the memory namespace."""
    embedder = get_embedder()
    vec = await asyncio.to_thread(embedder.embed_documents, [text])
    payload = [(fact_id, vec[0], metadata)]
    await asyncio.to_thread(store_upsert, payload, NAMESPACE)


async def query_facts(
    query_text: str,
    top_k: int = 5,
    metadata_filter: dict[str, Any] | None = None,
) -> list[Hit]:
    embedder = get_embedder()
    vec = await asyncio.to_thread(embedder.embed_query, query_text)
    return await asyncio.to_thread(
        store_query, vec, top_k, metadata_filter, NAMESPACE,
    )


async def delete_fact_vectors(fact_ids: list[str]) -> None:
    if not fact_ids:
        return
    await asyncio.to_thread(delete_ids, fact_ids, NAMESPACE)
