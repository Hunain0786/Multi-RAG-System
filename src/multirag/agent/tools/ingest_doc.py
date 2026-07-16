"""`ingest_doc` agent tool — ingest a file into the Pinecone doc index."""

from __future__ import annotations

from typing import Any

from multirag.rag.pipeline import ingest_file

NAME = "ingest_doc"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Ingest a document into the doc index. The file must already be on disk at "
        "`source_path` (uploaded via POST /docs/ingest or placed under ./docs). "
        "Idempotent by content hash — re-ingesting the same file is a no-op. Use only "
        "when the user explicitly asks to add a new document."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "source_path": {
                "type": "string",
                "description": "Absolute or workspace-relative path to a .txt / .md / .pdf.",
            },
            "doc_type": {
                "type": "string",
                "enum": ["policy", "manual", "faq", "other"],
                "description": "Corpus this document belongs to (also the Pinecone namespace).",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Free-form tags stored in Pinecone metadata for later filtering.",
            },
        },
        "required": ["source_path"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    result = await ingest_file(
        source_path=input_["source_path"],
        doc_type=input_.get("doc_type"),
        tags=input_.get("tags"),
    )
    return {
        "doc_id": result.doc_id,
        "chunks_added": result.chunks_added,
        "tokens": result.tokens,
        "reused": result.reused,
    }
