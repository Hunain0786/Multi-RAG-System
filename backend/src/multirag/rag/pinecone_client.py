"""Pinecone index singleton + idempotent `ensure_index` bootstrap.

Also runnable as a module (`python -m multirag.rag.pinecone_client`) so
`make pinecone-init` can call it before the app starts.
"""

from __future__ import annotations

from functools import lru_cache

from multirag.config import get_settings
from multirag.logging import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def get_pc():
    from pinecone import Pinecone

    settings = get_settings()
    if not settings.pinecone_api_key:
        raise RuntimeError("PINECONE_API_KEY is not set")
    return Pinecone(api_key=settings.pinecone_api_key)


def ensure_index() -> None:
    """Create the configured Pinecone serverless index if it doesn't exist."""
    from pinecone import ServerlessSpec

    settings = get_settings()
    pc = get_pc()
    name = settings.pinecone_index

    existing = {ix["name"] for ix in pc.list_indexes()}
    if name in existing:
        log.info("pinecone.index.exists", name=name)
        return

    log.info(
        "pinecone.index.creating",
        name=name,
        dim=settings.embed_dimensions,
        cloud=settings.pinecone_cloud,
        region=settings.pinecone_region,
    )
    pc.create_index(
        name=name,
        dimension=settings.embed_dimensions,
        metric="cosine",
        spec=ServerlessSpec(cloud=settings.pinecone_cloud, region=settings.pinecone_region),
    )
    log.info("pinecone.index.created", name=name)


@lru_cache(maxsize=1)
def get_index():
    settings = get_settings()
    return get_pc().Index(settings.pinecone_index)


if __name__ == "__main__":
    from multirag.logging import configure_logging

    configure_logging()
    ensure_index()
