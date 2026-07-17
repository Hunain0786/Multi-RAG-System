"""/memory — inspect and prune stored memory facts + last episode summary."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from multirag.config import get_settings
from multirag.memory import store, vector
from multirag.schemas.memory import (
    ConversationMemoryResponse,
    EpisodeSummary,
    FactKind,
    MemoryFactListResponse,
    MemoryFactSummary,
)

router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("", response_model=MemoryFactListResponse)
async def list_memory_facts(kind: FactKind | None = None) -> MemoryFactListResponse:
    settings = get_settings()
    rows = await store.list_facts(user_id=settings.memory_user_id, kind=kind)
    return MemoryFactListResponse(
        facts=[
            MemoryFactSummary(
                id=r.id,
                user_id=r.user_id,
                text=r.text,
                kind=r.kind,  # type: ignore[arg-type]
                confidence=r.confidence,
                source_conversation_id=r.source_conversation_id,
                created_at=r.created_at,
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.delete("/{fact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory_fact(fact_id: str) -> None:
    row = await store.get_fact(fact_id)
    if row is None:
        raise HTTPException(status_code=404, detail="fact not found")
    if row.deleted_at is not None:
        # Idempotent: already deleted is fine.
        return
    deleted = await store.soft_delete_fact(fact_id)
    if deleted:
        await vector.delete_fact_vectors([fact_id])


@router.get("/conversations/{conv_id}", response_model=ConversationMemoryResponse)
async def get_conversation_memory(conv_id: str) -> ConversationMemoryResponse:
    conv = await store.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    ep = await store.get_latest_episode(conv_id)
    return ConversationMemoryResponse(
        conversation_id=conv_id,
        latest_episode=(
            EpisodeSummary(
                id=ep.id,
                conversation_id=ep.conversation_id,
                from_seq=ep.from_seq,
                to_seq=ep.to_seq,
                summary=ep.summary,
                created_at=ep.created_at,
            )
            if ep is not None
            else None
        ),
    )
