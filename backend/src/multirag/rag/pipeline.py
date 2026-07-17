"""Ingestion pipeline: file -> chunks -> embeddings -> Pinecone + Doc row.

Idempotent by `sha256(text)` — re-ingesting the same file is a no-op that
returns the existing `doc_id`. Deleting a Doc cascades a delete of its
Pinecone vectors (IDs are deterministic: `{doc_id}#{chunk_index}`).

Also runnable as a module — walks the given directory and ingests every
supported file:

    python -m multirag.rag.pipeline ./docs
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import secrets
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row

from multirag.config import get_settings

# psycopg's async client refuses the default Windows ProactorEventLoop.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from multirag.logging import get_logger
from multirag.rag.chunking import Chunk, chunk_text
from multirag.rag.embedder import get_embedder
from multirag.rag.loaders import SUPPORTED_EXTS, load_file
from multirag.rag.store import delete_ids, upsert

log = get_logger(__name__)


@dataclass
class IngestResult:
    doc_id: str
    chunks_added: int
    tokens: int
    reused: bool  # True if we short-circuited because the sha256 already existed


def _infer_doc_type(path: Path, override: str | None) -> str:
    if override:
        return override
    lower = path.name.lower()
    if "polic" in lower:
        return "policy"
    if "warranty" in lower or "manual" in lower:
        return "manual"
    if "faq" in lower or "questions" in lower:
        return "faq"
    return "other"


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _estimate_tokens(text: str) -> int:
    # Rough heuristic (~4 chars/token). tiktoken would be more accurate but slower.
    return max(1, len(text) // 4)


async def ingest_file(
    source_path: str | Path,
    doc_type: str | None = None,
    tags: list[str] | None = None,
) -> IngestResult:
    settings = get_settings()
    path = Path(source_path).resolve()
    text = load_file(path)
    if not text.strip():
        raise ValueError(f"file '{path}' has no extractable text")

    sha = _sha256(text)
    resolved_type = _infer_doc_type(path, doc_type)

    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute("SELECT id, chunk_count, tokens FROM docs WHERE sha256 = %s;", (sha,))
            existing = await cur.fetchone()
            if existing:
                log.info("ingest.reused", doc_id=existing["id"], path=str(path))
                return IngestResult(
                    doc_id=existing["id"],
                    chunks_added=0,
                    tokens=existing["tokens"],
                    reused=True,
                )

            chunks: list[Chunk] = chunk_text(
                text, chunk_size=settings.chunk_size, chunk_overlap=settings.chunk_overlap
            )
            if not chunks:
                raise ValueError(f"file '{path}' produced no chunks")

            # Embed in-process (sync client — pinecone SDK is also sync).
            embedder = get_embedder()
            embeddings = await asyncio.to_thread(
                embedder.embed_documents, [c.text for c in chunks]
            )
            tokens = sum(_estimate_tokens(c.text) for c in chunks)

            # Insert Doc row first so we have a stable doc_id for chunk IDs.
            # Prisma's cuid() default is client-side; when we insert via psycopg
            # we must supply the id ourselves.
            doc_id = "doc_" + secrets.token_hex(12)
            await cur.execute(
                "INSERT INTO docs (id, source_path, doc_type, sha256, chunk_count, tokens, meta) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s);",
                (
                    doc_id,
                    str(path),
                    resolved_type,
                    sha,
                    len(chunks),
                    tokens,
                    json.dumps({"tags": tags or []}),
                ),
            )
            await conn.commit()

    # Upsert vectors into the default namespace; doc_type lives in metadata.
    vectors: list[tuple[str, list[float], dict[str, Any]]] = []
    for c, emb in zip(chunks, embeddings, strict=True):
        vid = f"{doc_id}#{c.index}"
        meta = {
            "doc_id": doc_id,
            "chunk_index": c.index,
            "text": c.text,
            "source_path": str(path),
            "doc_type": resolved_type,
            "tags": tags or [],
            "tokens": _estimate_tokens(c.text),
        }
        vectors.append((vid, emb, meta))

    upsert(vectors)

    log.info(
        "ingest.done",
        doc_id=doc_id,
        path=str(path),
        chunks=len(chunks),
        doc_type=resolved_type,
    )
    return IngestResult(doc_id=doc_id, chunks_added=len(chunks), tokens=tokens, reused=False)


async def delete_doc(doc_id: str) -> None:
    settings = get_settings()
    async with await psycopg.AsyncConnection.connect(settings.database_url) as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                "SELECT chunk_count FROM docs WHERE id = %s;", (doc_id,)
            )
            row = await cur.fetchone()
            if not row:
                return
            n = int(row["chunk_count"])
            await cur.execute("DELETE FROM docs WHERE id = %s;", (doc_id,))
            await conn.commit()

    ids = [f"{doc_id}#{i}" for i in range(n)]
    delete_ids(ids)
    log.info("doc.deleted", doc_id=doc_id, chunks=n)


async def _ingest_directory(root: str) -> None:
    from multirag.logging import configure_logging

    configure_logging()
    p = Path(root)
    if not p.exists():
        raise SystemExit(f"path not found: {p}")

    files: list[Path]
    if p.is_dir():
        files = sorted(
            f for f in p.rglob("*")
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTS and "_uploads" not in f.parts
        )
    else:
        files = [p]

    if not files:
        print(f"no supported files found under {p}")
        return

    for f in files:
        try:
            r = await ingest_file(f)
            marker = "reused" if r.reused else "new"
            print(f"[{marker}] {f}  doc_id={r.doc_id}  chunks={r.chunks_added}")
        except Exception as e:  # noqa: BLE001
            print(f"[error] {f}: {e}")


if __name__ == "__main__":
    root = sys.argv[1] if len(sys.argv) > 1 else "./docs"
    asyncio.run(_ingest_directory(root))
