"""`search_docs` agent tool — semantic top-k over Pinecone."""

from __future__ import annotations

from typing import Any

from multirag.rag.retriever import search

NAME = "search_docs"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Semantic search over the ingested documents (policies, manuals, FAQs). "
        "Use for questions grounded in prose (return policy, warranty details, "
        "how-to instructions, FAQ answers). "
        "IMPORTANT: leave `doc_type` UNSET by default so the search spans every "
        "corpus — a question about 'warranty' may live in a manual, an FAQ, or a "
        "policy doc, and pre-filtering by doc_type is the leading cause of "
        "false-negative retrievals. Only set doc_type when the user explicitly "
        "names the corpus (e.g. 'in the FAQ...', 'what does the manual say...')."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 6},
            "doc_type": {
                "type": "string",
                "enum": ["policy", "manual", "faq", "other"],
                "description": (
                    "OPTIONAL. Scope search to one doc_type via metadata filter. "
                    "Leave unset unless the user explicitly names the corpus."
                ),
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Filter to chunks whose tags intersect this list.",
            },
        },
        "required": ["query"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    hits = await search(
        query=input_["query"],
        top_k=int(input_.get("top_k", 6)),
        doc_type=input_.get("doc_type"),
        tags=input_.get("tags"),
    )
    return {
        "query": input_["query"],
        "hits": [
            {
                "doc_id": h.doc_id,
                "chunk_index": h.chunk_index,
                "source_path": h.source_path,
                "doc_type": h.doc_type,
                "score": round(h.score, 4),
                "text": h.text,
                "tags": h.tags,
            }
            for h in hits
        ],
    }
