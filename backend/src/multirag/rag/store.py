"""Pinecone adapter: upsert / query / delete.

Design note: doc chunks live in Pinecone's DEFAULT namespace and are scoped by
`doc_type` via metadata filter. Agent memory facts use a distinct
`namespace="memory"` for hard isolation from doc content. Namespaces stay
reserved for the (few) categories that need this hard separation; per-corpus
scoping still goes through metadata filtering.
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


def upsert(
    vectors: list[tuple[str, list[float], dict[str, Any]]],
    namespace: str | None = None,
) -> int:
    """Upsert (id, vector, metadata) triples. Empty/None namespace = default."""
    if not vectors:
        return 0
    index = get_index()
    written = 0
    for i in range(0, len(vectors), UPSERT_BATCH_SIZE):
        batch = vectors[i:i + UPSERT_BATCH_SIZE]
        payload = [{"id": vid, "values": vec, "metadata": meta} for vid, vec, meta in batch]
        kwargs: dict[str, Any] = {"vectors": payload}
        if namespace:
            kwargs["namespace"] = namespace
        index.upsert(**kwargs)
        written += len(payload)
    log.info("pinecone.upsert", count=written, namespace=namespace or "")
    return written


def query(
    vector: list[float],
    top_k: int = 6,
    metadata_filter: dict[str, Any] | None = None,
    namespace: str | None = None,
) -> list[Hit]:
    index = get_index()
    kwargs: dict[str, Any] = {
        "vector": vector,
        "top_k": top_k,
        "include_metadata": True,
        "include_values": False,
        "filter": metadata_filter or None,
    }
    if namespace:
        kwargs["namespace"] = namespace
    resp = index.query(**kwargs)
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
        kwargs: dict[str, Any] = {"ids": ids[i:i + 1000]}
        if namespace:
            kwargs["namespace"] = namespace
        index.delete(**kwargs)
    log.info("pinecone.delete", count=len(ids), namespace=namespace or "")


def delete_namespace(namespace: str) -> None:
    """Drop all vectors from a legacy namespace. Used during migration."""
    index = get_index()
    try:
        index.delete(delete_all=True, namespace=namespace)
        log.info("pinecone.delete_namespace", namespace=namespace)
    except Exception as e:  # noqa: BLE001
        log.warning("pinecone.delete_namespace.failed", namespace=namespace, error=str(e))
