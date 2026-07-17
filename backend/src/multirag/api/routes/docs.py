"""/docs — READ-ONLY listing + delete for the ingested-doc registry.

Ingestion is intentionally NOT exposed as an HTTP endpoint. New corpora are
added out-of-band via the CLI so what the LLM can search is curated:

    make ingest                                                 # ingests ./docs/
    python -m multirag.rag.pipeline ./path/to/file.pdf policy   # single file

Delete stays on HTTP so operators can prune stale docs without touching the DB.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status
from psycopg.rows import dict_row

from multirag.db.pool import fetch_conn
from multirag.rag.pipeline import delete_doc
from multirag.schemas.ingest import DocListResponse, DocSummary, DocType

router = APIRouter(prefix="/docs", tags=["docs"])


@router.get("", response_model=DocListResponse)
async def list_docs(doc_type: DocType | None = None) -> DocListResponse:
    where = "TRUE"
    params: list[Any] = []
    if doc_type is not None:
        where = "doc_type = %s"
        params.append(doc_type)

    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"SELECT id, source_path, doc_type, sha256, chunk_count, tokens, "
                f"ingested_at, meta FROM docs WHERE {where} ORDER BY ingested_at DESC;",
                params,
            )
            rows = await cur.fetchall()

    return DocListResponse(
        docs=[DocSummary(**r) for r in rows],
        total=len(rows),
    )


@router.delete("/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete(doc_id: str) -> None:
    await delete_doc(doc_id)
