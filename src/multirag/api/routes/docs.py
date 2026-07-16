"""/docs — upload / list / delete ingested documents."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from psycopg.rows import dict_row

from multirag.api.deps import uploads_dir_dep
from multirag.db.pool import fetch_conn
from multirag.rag.loaders import SUPPORTED_EXTS
from multirag.rag.pipeline import delete_doc, ingest_file
from multirag.schemas.ingest import DocListResponse, DocSummary, DocType, IngestResponse

router = APIRouter(prefix="/docs", tags=["docs"])


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest(
    file: UploadFile = File(..., description=".txt / .md / .pdf"),
    doc_type: DocType | None = Form(default=None),
    tags: str | None = Form(default=None, description="Comma-separated tags"),
    uploads_dir: Path = Depends(uploads_dir_dep),
) -> IngestResponse:
    filename = file.filename or "upload.bin"
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(400, f"Unsupported extension '{ext}'. Supported: {sorted(SUPPORTED_EXTS)}")

    dest = uploads_dir / filename
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    result = await ingest_file(source_path=dest, doc_type=doc_type, tags=tag_list)

    return IngestResponse(
        doc_id=result.doc_id,
        chunks_added=result.chunks_added,
        tokens=result.tokens,
        reused=result.reused,
        source_path=str(dest),
    )


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
