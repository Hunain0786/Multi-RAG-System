"""Pinecone adapter: upsert / query / delete.

Design note: everything lives in Pinecone's DEFAULT namespace. Scoping by
`doc_type` is done via metadata filter (`{"doc_type": ...}`) so a single query
can either search across all corpora or scope to one. Namespaces stay reserved
for future per-tenant hard isolation.
"""

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


def upsert(vectors: list[tuple[str, list[float], dict[str, Any]]]) -> int:
    """Upsert (id, vector, metadata) triples into the default namespace."""
    if not vectors:
        return 0
    index = get_index()
    written = 0
    for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
        batch = vectors[i:i + UPSERT_BATCH_SIZE]
        payload = [{"id": vid, "values": vec, "metadata": meta} for vid, vec, meta in batch]
        index.upsert(vectors=payload)
        written += len(payload)
    log.info("pinecone.upsert", count=written)
    return written


def query(
    vector: list[float],
    top_k: int = 6,
    metadata_filter: dict[str, Any] | None = None,
) -> list[Hit]:
    index = get_index()
    resp = index.query(
        vector=vector,
        top_k=top_k,
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


def delete_ids(ids: list[str]) -> None:
    if not ids:
        return
    index = get_index()
    for i in range(0, len(ids), 1000):
        index.delete(ids=ids[i:i + 1000])
    log.info("pinecone.delete", count=len(ids))


def delete_namespace(namespace: str) -> None:
    """Drop all vectors from a legacy namespace. Used during migration."""
    index = get_index()
    try:
        index.delete(delete_all=True, namespace=namespace)
        log.info("pinecone.delete_namespace", namespace=namespace)
    except Exception as e:  # noqa: BLE001
        log.warning("pinecone.delete_namespace.failed", namespace=namespace, error=str(e))
