"""/documents — upload / list / delete ingested documents.

Upload via POST /documents/ingest (multipart). Prefix is intentionally NOT
`/docs` — FastAPI reserves `/docs` for Swagger UI by default.

The agent still cannot ingest (`ingest_doc` is not registered). CLI ingest
(`make ingest`) remains supported for bulk / sample corpora.
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path
from typing import Any, get_args

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from psycopg.rows import dict_row

from multirag.api.deps import uploads_dir_dep
from multirag.db.pool import fetch_conn
from multirag.logging import get_logger
from multirag.rag.loaders import SUPPORTED_EXTS
from multirag.rag.pipeline import delete_doc, ingest_file
from multirag.schemas.ingest import DocListResponse, DocSummary, DocType, IngestResponse

router = APIRouter(prefix="/documents", tags=["documents"])
log = get_logger(__name__)

_SAFE_STEM = re.compile(r"[^A-Za-z0-9._-]+")
_DOC_TYPES = set(get_args(DocType))  # {"policy", "manual", "faq", "other"}


def _safe_filename(name: str) -> str:
    """Sanitize a basename while always preserving a real extension."""
    base = Path(name).name.strip() or "upload.bin"
    ext = Path(base).suffix.lower()
    stem = Path(base).stem
    stem = _SAFE_STEM.sub("_", stem).strip("._") or "upload"
    stem = stem[:80]
    if ext not in SUPPORTED_EXTS:
        # Keep whatever suffix we got so the caller can reject it clearly.
        ext = ext[:16] if ext else ""
    return f"{stem}{ext}"


def _parse_doc_type(raw: str | None) -> DocType | None:
    if raw is None:
        return None
    value = raw.strip().lower()
    if not value or value == "auto":
        return None
    if value not in _DOC_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_type '{raw}'. Expected one of: {sorted(_DOC_TYPES)}",
        )
    return value  # type: ignore[return-value]


def _friendly_ingest_error(exc: ValueError, ext: str) -> str:
    msg = str(exc)
    if "no extractable text" in msg or "produced no chunks" in msg:
        if ext == ".pdf":
            return (
                "No extractable text in this PDF. Scanned/image-only PDFs aren't "
                "supported — use a text-based PDF, .txt, or .md."
            )
        return "File is empty or has no extractable text. Upload a non-empty .txt, .md, or text PDF."
    return msg


@router.post("/ingest", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest(
    file: UploadFile = File(..., description=".txt / .md / .pdf"),
    # Plain str so "auto"/"" don't trip Literal validation with a 422.
    doc_type: str | None = Form(default=None),
    tags: str | None = Form(default=None, description="Comma-separated tags"),
    uploads_dir: Path = Depends(uploads_dir_dep),
) -> IngestResponse:
    filename = _safe_filename(file.filename or "upload.bin")
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension '{ext or '(none)'}'. Supported: {sorted(SUPPORTED_EXTS)}",
        )

    resolved_type = _parse_doc_type(doc_type)

    content = await file.read()
    await file.close()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty (0 bytes).")

    # Unique prefix avoids clobbering prior uploads of the same name.
    dest = uploads_dir / f"{secrets.token_hex(4)}_{filename}"
    try:
        dest.write_bytes(content)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to stage upload: {e}") from e

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]
    try:
        result = await ingest_file(
            source_path=dest, doc_type=resolved_type, tags=tag_list
        )
    except ValueError as e:
        log.warning("ingest.rejected", path=str(dest), error=str(e))
        raise HTTPException(status_code=400, detail=_friendly_ingest_error(e, ext)) from e
    except Exception as e:  # noqa: BLE001 — surface pipeline failures cleanly
        log.exception("ingest.failed", path=str(dest))
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}") from e

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
