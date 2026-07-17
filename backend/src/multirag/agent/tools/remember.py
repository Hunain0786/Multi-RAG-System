"""`remember` agent tool — persist a user-level fact/preference/constraint."""

from __future__ import annotations

from typing import Any

from multirag.agent.context import current_conversation_id
from multirag.config import get_settings
from multirag.memory import store, vector

NAME = "remember"

_ALLOWED_KINDS = {"preference", "fact", "constraint"}

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Persist a durable memory the user wants you to keep across sessions. "
        "Use ONLY when the user explicitly says 'remember X', 'from now on Y', "
        "or states a stable preference / constraint. Never invent memories from "
        "an offhand comment. Keep the `text` short and self-contained (one "
        "sentence). The `kind` field categorises the memory."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "text": {
                "type": "string",
                "description": "The fact to remember. Keep it terse and self-contained.",
            },
            "kind": {
                "type": "string",
                "enum": sorted(_ALLOWED_KINDS),
                "description": (
                    "preference = user preference (default currencies, timezones); "
                    "fact = stable factual claim about the user or their business; "
                    "constraint = a hard rule to apply on future queries."
                ),
            },
        },
        "required": ["text", "kind"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    text = str(input_["text"]).strip()
    kind = str(input_["kind"]).strip().lower()
    if not text:
        raise ValueError("`text` must be non-empty")
    if kind not in _ALLOWED_KINDS:
        raise ValueError(
            f"`kind` must be one of {sorted(_ALLOWED_KINDS)} (got {kind!r})",
        )

    settings = get_settings()
    row = await store.create_fact(
        text=text,
        kind=kind,
        user_id=settings.memory_user_id,
        source_conversation_id=current_conversation_id(),
        confidence=1.0,
    )
    await vector.upsert_fact_vector(
        fact_id=row.id,
        text=text,
        metadata={
            "user_id": row.user_id,
            "kind": row.kind,
            "text": text,
            "source_conversation_id": row.source_conversation_id or "",
        },
    )
    return {
        "id": row.id,
        "text": row.text,
        "kind": row.kind,
        "created_at": row.created_at.isoformat(),
    }
