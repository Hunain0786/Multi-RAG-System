"""Pydantic models for the /chat endpoint."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str | list[dict[str, Any]]


class ChatRequest(BaseModel):
    conversation_id: str | None = Field(
        default=None,
        description=(
            "Existing conversation to append to. If omitted, a new conversation "
            "is created and its id is emitted as the first SSE event."
        ),
    )
    messages: list[ChatMessage] = Field(
        ...,
        description=(
            "Conversation history. Last message must be role='user'. Prior "
            "messages are ignored — Postgres is the source of truth for history."
        ),
    )


class StreamedEvent(BaseModel):
    type: Literal["conversation", "text", "tool_use", "tool_result", "stop", "error"]
    data: dict[str, Any] = Field(default_factory=dict)
