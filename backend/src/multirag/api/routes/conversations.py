"""/conversations — list past chats, load history, rename, delete."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from multirag.config import get_settings
from multirag.memory import store
from multirag.schemas.memory import (
    ConversationListResponse,
    ConversationMessagesResponse,
    ConversationSummary,
    PersistedMessage,
    RenameConversationRequest,
)

router = APIRouter(prefix="/conversations", tags=["conversations"])


@router.get("", response_model=ConversationListResponse)
async def list_conversations() -> ConversationListResponse:
    settings = get_settings()
    rows = await store.list_conversations(user_id=settings.memory_user_id)
    return ConversationListResponse(
        conversations=[
            ConversationSummary(
                id=r.id,
                user_id=r.user_id,
                title=r.title,
                message_count=r.message_count,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in rows
        ],
        total=len(rows),
    )


@router.get("/{conv_id}/messages", response_model=ConversationMessagesResponse)
async def get_conversation_messages(conv_id: str) -> ConversationMessagesResponse:
    conv = await store.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    rows = await store.get_messages(conv_id)
    return ConversationMessagesResponse(
        conversation_id=conv_id,
        messages=[
            PersistedMessage(
                id=r.id,
                seq=r.seq,
                role=r.role,  # type: ignore[arg-type]
                content=r.content,
                created_at=r.created_at,
            )
            for r in rows
        ],
    )


@router.patch("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def rename_conversation(conv_id: str, req: RenameConversationRequest) -> None:
    conv = await store.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    # `set_conversation_title` only fills empty titles; use raw UPDATE to allow rename.
    from multirag.db.pool import fetch_conn  # local import to keep top clean
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE conversations SET title = %s, updated_at = NOW() WHERE id = %s",
                (req.title, conv_id),
            )
        await conn.commit()


@router.delete("/{conv_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(conv_id: str) -> None:
    conv = await store.get_conversation(conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="conversation not found")
    await store.delete_conversation(conv_id)
