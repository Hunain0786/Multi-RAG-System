"""Pydantic models for /conversations and /memory endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class ConversationSummary(BaseModel):
    id: str
    user_id: str
    title: str | None
    message_count: int
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummary]
    total: int


class PersistedMessage(BaseModel):
    id: str
    seq: int
    role: Literal["user", "assistant"]
    content: list[dict[str, Any]]
    created_at: datetime


class ConversationMessagesResponse(BaseModel):
    conversation_id: str
    messages: list[PersistedMessage]


class RenameConversationRequest(BaseModel):
    title: str


# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

FactKind = Literal["preference", "fact", "constraint"]


class MemoryFactSummary(BaseModel):
    id: str
    user_id: str
    text: str
    kind: FactKind
    confidence: float
    source_conversation_id: str | None
    created_at: datetime


class MemoryFactListResponse(BaseModel):
    facts: list[MemoryFactSummary]
    total: int


class EpisodeSummary(BaseModel):
    id: str
    conversation_id: str
    from_seq: int
    to_seq: int
    summary: str
    created_at: datetime


class ConversationMemoryResponse(BaseModel):
    """Combines the facts scoped to a conversation with its latest summary."""
    conversation_id: str
    latest_episode: EpisodeSummary | None
