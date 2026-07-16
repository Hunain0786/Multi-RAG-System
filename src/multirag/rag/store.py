"""Pinecone adapter: upsert / query / delete."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from multirag.logging import get_logger
from multirag.rag.pinecone_client import get_index

log = get_logger(__name__)

UPSERT_BATCH_SIZE = 96


@dataclass
class Hit:
    id: str
    score: float
    metadata: dict[str, Any]


def upsert(
    vectors: list[tuple[str, list[float], dict[str, Any]]],
    namespace: str | None = None,
) -> int:
    """Upsert (id, vector, metadata) triples. Returns count written."""
    if not vectors:
        return 0
    index = get_index()
    written = 0
    for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
        batch = vectors[i:i + UPSERT_BATCH_SIZE]
        payload = [{"id": vid, "values": vec, "metadata": meta} for vid, vec, meta in batch]
        index.upsert(vectors=payload, namespace=namespace or "")
        written += len(payload)
    log.info("pinecone.upsert", count=written, namespace=namespace or "(default)")
    return written


def query(
    vector: list[float],
    top_k: int = 6,
    namespace: str | None = None,
    metadata_filter: dict[str, Any] | None = None,
) -> list[Hit]:
    index = get_index()
    resp = index.query(
        vector=vector,
        top_k=top_k,
        namespace=namespace or "",
        include_metadata=True,
        include_values=False,
        filter=metadata_filter or None,
    )
    matches = resp.get("matches", []) if isinstance(resp, dict) else resp.matches
    hits: list[Hit] = []
    for m in matches:
        if isinstance(m, dict):
            hits.append(Hit(id=m["id"], score=float(m.get("score", 0.0)),
                            metadata=m.get("metadata", {}) or {}))
        else:
            hits.append(Hit(id=m.id, score=float(m.score or 0.0),
                            metadata=dict(m.metadata or {})))
    return hits


def delete_ids(ids: list[str], namespace: str | None = None) -> None:
    if not ids:
        return
    index = get_index()
    for i in range(0, len(ids), 1000):
        index.delete(ids=ids[i:i + 1000], namespace=namespace or "")
    log.info("pinecone.delete", count=len(ids), namespace=namespace or "(default)")
