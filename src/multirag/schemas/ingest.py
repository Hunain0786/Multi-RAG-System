"""Pydantic models for the /docs endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

DocType = Literal["policy", "manual", "faq", "other"]


class IngestResponse(BaseModel):
    doc_id: str
    chunks_added: int
    tokens: int
    reused: bool
    source_path: str


class DocSummary(BaseModel):
    id: str
    source_path: str
    doc_type: DocType
    sha256: str
    chunk_count: int
    tokens: int
    ingested_at: datetime
    meta: dict[str, Any]


class DocListResponse(BaseModel):
    docs: list[DocSummary]
    total: int
