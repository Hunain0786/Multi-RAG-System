"""Assemble a memory context block that gets prepended to the agent's system
prompt for each turn.

Two ingredients:
  1. `MemoryFact`s retrieved by semantic similarity to the user's current query,
     ranked with a mild recency bump.
  2. The latest `MemoryEpisode` summary for the conversation (if any).

Both are optional; when neither exists we return None and the loop skips
injection entirely.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone

from multirag.logging import get_logger
from multirag.memory import store, vector

log = get_logger(__name__)

# Weightings for fact ranking.
_SCORE_WEIGHT = 1.0
_RECENCY_WEIGHT = 0.15  # 0.15 * exp(-age_days / half_life)
_RECENCY_HALF_LIFE_DAYS = 30.0
_MIN_SIMILARITY = 0.55  # drop obviously unrelated hits


@dataclass
class RecalledFact:
    id: str
    text: str
    kind: str
    score: float
    similarity: float
    created_at: datetime


async def recall_facts(
    query: str,
    user_id: str = "local",
    top_k: int = 5,
) -> list[RecalledFact]:
    """Semantic + recency ranked facts for a user query."""
    if not query.strip():
        return []
    hits = await vector.query_facts(
        query_text=query,
        top_k=top_k * 3,
        metadata_filter={"user_id": user_id},
    )
    if not hits:
        return []
    rows = await store.get_facts_by_ids([h.id for h in hits])
    by_id = {r.id: r for r in rows}

    now = datetime.now(timezone.utc)
    ranked: list[RecalledFact] = []
    for h in hits:
        row = by_id.get(h.id)
        if row is None:
            continue
        if h.score < _MIN_SIMILARITY:
            continue
        age_days = max(0.0, (now - row.created_at).total_seconds() / 86400.0)
        recency = math.exp(-age_days / _RECENCY_HALF_LIFE_DAYS)
        score = _SCORE_WEIGHT * h.score + _RECENCY_WEIGHT * recency
        ranked.append(
            RecalledFact(
                id=row.id,
                text=row.text,
                kind=row.kind,
                score=score,
                similarity=h.score,
                created_at=row.created_at,
            ),
        )
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked[:top_k]


async def build_memory_context(
    query: str,
    conversation_id: str | None,
    user_id: str = "local",
    top_k: int = 5,
) -> str | None:
    """Return an assembled memory block, or None if there's nothing to inject."""
    facts = await recall_facts(query=query, user_id=user_id, top_k=top_k)

    summary: str | None = None
    if conversation_id:
        ep = await store.get_latest_episode(conversation_id)
        if ep is not None:
            summary = ep.summary

    if not facts and not summary:
        return None

    lines: list[str] = ["## Memory context (for grounding your response)"]
    if summary:
        lines.append("")
        lines.append("### Recent conversation summary")
        lines.append(summary.strip())
    if facts:
        lines.append("")
        lines.append("### Relevant remembered facts")
        for f in facts:
            lines.append(f"- ({f.kind}) {f.text}")
    lines.append("")
    lines.append(
        "Use this context to keep answers consistent with prior turns and known "
        "preferences. Do NOT treat facts as ground truth for policy or numeric "
        "questions — always call the appropriate tool for those.",
    )
    return "\n".join(lines)
