"""Semantic retrieval over the Pinecone index."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any

from multirag.rag.embedder import get_embedder
from multirag.rag.store import query as store_query


@dataclass
class RetrievedChunk:
    doc_id: str
    chunk_index: int
    text: str
    source_path: str
    doc_type: str
    score: float
    tags: list[str]


async def search(
    query: str,
    top_k: int = 6,
    doc_type: str | None = None,
    tags: list[str] | None = None,
    metadata_filter: dict[str, Any] | None = None,
) -> list[RetrievedChunk]:
    """Semantic search. Scopes by metadata (`doc_type`, `tags`), not namespace."""
    if not query.strip():
        return []

    embedder = get_embedder()
    vector = await asyncio.to_thread(embedder.embed_query, query)

    flt = dict(metadata_filter or {})
    if doc_type:
        flt["doc_type"] = doc_type
    if tags:
        flt.setdefault("tags", {"$in": tags})

    hits = await asyncio.to_thread(store_query, vector, top_k, flt or None)

    return [
        RetrievedChunk(
            doc_id=h.metadata.get("doc_id", ""),
            chunk_index=int(h.metadata.get("chunk_index", 0)),
            text=h.metadata.get("text", ""),
            source_path=h.metadata.get("source_path", ""),
            doc_type=h.metadata.get("doc_type", ""),
            score=h.score,
            tags=list(h.metadata.get("tags", []) or []),
        )
        for h in hits
    ]
