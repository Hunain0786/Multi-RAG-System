"""`recall` agent tool — explicit semantic search over stored memory facts."""

from __future__ import annotations

from typing import Any

from multirag.config import get_settings
from multirag.memory import recall as memory_recall

NAME = "recall"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Semantic search over previously stored memories (see `remember`). Use "
        "when you need to double-check user preferences before answering or "
        "when the automatic memory injection didn't surface something obviously "
        "relevant. Returns nothing if no stored memory is close enough."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5},
        },
        "required": ["query"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    top_k = int(input_.get("top_k", 5))
    hits = await memory_recall.recall_facts(
        query=str(input_["query"]),
        user_id=settings.memory_user_id,
        top_k=top_k,
    )
    return {
        "query": input_["query"],
        "hits": [
            {
                "id": h.id,
                "text": h.text,
                "kind": h.kind,
                "similarity": round(h.similarity, 4),
                "created_at": h.created_at.isoformat(),
            }
            for h in hits
        ],
    }
