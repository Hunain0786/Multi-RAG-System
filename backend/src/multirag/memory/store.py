"""Postgres CRUD for the agent memory tables.

Design:
- Ids are generated in Python via `secrets.token_hex(12)` to match the rest of
  the app (Prisma uses cuid() client-side, we don't want to depend on the Prisma
  runtime from Python — psycopg is the reader).
- `Message.content` is always a list of Anthropic content blocks:
    text        : {"type": "text", "text": ...}
    tool_use    : {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
    tool_result : {"type": "tool_result", "tool_use_id": ..., "content": ..., "is_error": ...}
- Message.seq is dense per-conversation, computed inside a single INSERT to
  avoid a read-modify-write round trip.
"""

from __future__ import annotations

import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Json

from multirag.db.pool import fetch_conn


# ---------------------------------------------------------------------------
# Ids + dataclasses
# ---------------------------------------------------------------------------

def new_id() -> str:
    return secrets.token_hex(12)


@dataclass
class ConversationRow:
    id: str
    user_id: str
    title: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0


@dataclass
class MessageRow:
    id: str
    conversation_id: str
    seq: int
    role: str
    content: list[dict[str, Any]]
    created_at: datetime


@dataclass
class MemoryFactRow:
    id: str
    user_id: str
    text: str
    kind: str
    confidence: float
    source_conversation_id: str | None
    created_at: datetime
    deleted_at: datetime | None


@dataclass
class MemoryEpisodeRow:
    id: str
    conversation_id: str
    from_seq: int
    to_seq: int
    summary: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

async def create_conversation(user_id: str = "local", title: str | None = None) -> str:
    conv_id = new_id()
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                VALUES (%s, %s, %s, NOW(), NOW())
                """,
                (conv_id, user_id, title),
            )
        await conn.commit()
    return conv_id


async def get_conversation(conv_id: str) -> ConversationRow | None:
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
                       COALESCE((SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id), 0) AS message_count
                FROM conversations c WHERE c.id = %s
                """,
                (conv_id,),
            )
            row = await cur.fetchone()
    return ConversationRow(**row) if row else None


async def list_conversations(user_id: str = "local", limit: int = 50) -> list[ConversationRow]:
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT c.id, c.user_id, c.title, c.created_at, c.updated_at,
                       COALESCE((SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id), 0) AS message_count
                FROM conversations c
                WHERE c.user_id = %s
                ORDER BY c.updated_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            rows = await cur.fetchall()
    return [ConversationRow(**r) for r in rows]


async def set_conversation_title(conv_id: str, title: str) -> None:
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE conversations SET title = %s, updated_at = NOW()
                WHERE id = %s AND title IS NULL
                """,
                (title, conv_id),
            )
        await conn.commit()


async def touch_conversation(conv_id: str) -> None:
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conv_id,),
            )
        await conn.commit()


async def delete_conversation(conv_id: str) -> None:
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            # Cascades to messages + episodes via FK.
            await cur.execute("DELETE FROM conversations WHERE id = %s", (conv_id,))
        await conn.commit()


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

async def append_message(
    conversation_id: str,
    role: str,
    content: list[dict[str, Any]],
) -> MessageRow:
    """Insert a message with the next dense seq. Content stored as JSONB."""
    msg_id = new_id()
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO messages (id, conversation_id, seq, role, content, created_at)
                VALUES (
                    %s, %s,
                    COALESCE((SELECT MAX(seq) + 1 FROM messages WHERE conversation_id = %s), 0),
                    %s, %s, NOW()
                )
                RETURNING id, conversation_id, seq, role, content, created_at
                """,
                (msg_id, conversation_id, conversation_id, role, Json(content)),
            )
            row = await cur.fetchone()
            await cur.execute(
                "UPDATE conversations SET updated_at = NOW() WHERE id = %s",
                (conversation_id,),
            )
        await conn.commit()
    assert row is not None
    row["content"] = _coerce_content(row["content"])
    return MessageRow(**row)


async def get_messages(conversation_id: str, from_seq: int = 0) -> list[MessageRow]:
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, conversation_id, seq, role, content, created_at
                FROM messages
                WHERE conversation_id = %s AND seq >= %s
                ORDER BY seq ASC
                """,
                (conversation_id, from_seq),
            )
            rows = await cur.fetchall()
    return [MessageRow(**{**r, "content": _coerce_content(r["content"])}) for r in rows]


async def count_messages(conversation_id: str) -> int:
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "SELECT COUNT(*) FROM messages WHERE conversation_id = %s",
                (conversation_id,),
            )
            row = await cur.fetchone()
    return int(row[0]) if row else 0


def _coerce_content(v: Any) -> list[dict[str, Any]]:
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        return json.loads(v)
    return list(v or [])


# ---------------------------------------------------------------------------
# Memory facts
# ---------------------------------------------------------------------------

async def create_fact(
    text: str,
    kind: str,
    user_id: str = "local",
    source_conversation_id: str | None = None,
    confidence: float = 1.0,
) -> MemoryFactRow:
    fact_id = new_id()
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO memory_facts
                    (id, user_id, text, kind, confidence, source_conversation_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id, user_id, text, kind, confidence,
                          source_conversation_id, created_at, deleted_at
                """,
                (fact_id, user_id, text, kind, confidence, source_conversation_id),
            )
            row = await cur.fetchone()
        await conn.commit()
    assert row is not None
    return MemoryFactRow(**row)


async def list_facts(
    user_id: str = "local",
    kind: str | None = None,
    include_deleted: bool = False,
    limit: int = 200,
) -> list[MemoryFactRow]:
    clauses = ["user_id = %s"]
    params: list[Any] = [user_id]
    if kind is not None:
        clauses.append("kind = %s")
        params.append(kind)
    if not include_deleted:
        clauses.append("deleted_at IS NULL")
    params.append(limit)
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                f"""
                SELECT id, user_id, text, kind, confidence,
                       source_conversation_id, created_at, deleted_at
                FROM memory_facts
                WHERE {' AND '.join(clauses)}
                ORDER BY created_at DESC
                LIMIT %s
                """,
                params,
            )
            rows = await cur.fetchall()
    return [MemoryFactRow(**r) for r in rows]


async def get_fact(fact_id: str) -> MemoryFactRow | None:
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, user_id, text, kind, confidence,
                       source_conversation_id, created_at, deleted_at
                FROM memory_facts WHERE id = %s
                """,
                (fact_id,),
            )
            row = await cur.fetchone()
    return MemoryFactRow(**row) if row else None


async def get_facts_by_ids(fact_ids: list[str]) -> list[MemoryFactRow]:
    if not fact_ids:
        return []
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, user_id, text, kind, confidence,
                       source_conversation_id, created_at, deleted_at
                FROM memory_facts WHERE id = ANY(%s) AND deleted_at IS NULL
                """,
                (fact_ids,),
            )
            rows = await cur.fetchall()
    return [MemoryFactRow(**r) for r in rows]


async def soft_delete_fact(fact_id: str) -> bool:
    async with fetch_conn() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                """
                UPDATE memory_facts SET deleted_at = NOW()
                WHERE id = %s AND deleted_at IS NULL
                """,
                (fact_id,),
            )
            affected = cur.rowcount
        await conn.commit()
    return affected > 0


# ---------------------------------------------------------------------------
# Memory episodes (rolling summaries)
# ---------------------------------------------------------------------------

async def add_episode(
    conversation_id: str,
    from_seq: int,
    to_seq: int,
    summary: str,
) -> MemoryEpisodeRow:
    ep_id = new_id()
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                INSERT INTO memory_episodes
                    (id, conversation_id, from_seq, to_seq, summary, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING id, conversation_id, from_seq, to_seq, summary, created_at
                """,
                (ep_id, conversation_id, from_seq, to_seq, summary),
            )
            row = await cur.fetchone()
        await conn.commit()
    assert row is not None
    return MemoryEpisodeRow(**row)


async def get_latest_episode(conversation_id: str) -> MemoryEpisodeRow | None:
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                """
                SELECT id, conversation_id, from_seq, to_seq, summary, created_at
                FROM memory_episodes
                WHERE conversation_id = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (conversation_id,),
            )
            row = await cur.fetchone()
    return MemoryEpisodeRow(**row) if row else None
