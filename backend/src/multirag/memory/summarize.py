"""Rolling per-conversation summariser.

Opt-in via `settings.memory_auto_summarize`. When enabled, after a chat turn
completes we check whether unsummarised message count > threshold and, if so,
call a *cheap* LLM prompt to fold the older messages into a single summary and
persist it as a `MemoryEpisode`. The next recall pulls that summary instead of
re-sending every early message.

Cost note: uses the same Anthropic model as the main agent but with
significantly lower max_tokens and no tools.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

from anthropic import Anthropic

from multirag.config import get_settings
from multirag.logging import get_logger
from multirag.memory import store

log = get_logger(__name__)

SUMMARY_MAX_TOKENS = 512
SUMMARY_TRIGGER_THRESHOLD = 12  # summarise once unsummarised messages exceed this
KEEP_TAIL = 4                    # always leave the last N raw for context


async def maybe_summarize(conversation_id: str) -> None:
    """Fire-and-forget entrypoint called from agent.loop after `stop`.

    Silently no-ops if disabled, if there's nothing new to summarise, or if the
    Anthropic call fails. Never raises to the caller.
    """
    settings = get_settings()
    if not settings.memory_auto_summarize:
        return
    if not settings.anthropic_api_key:
        return
    try:
        await _run(conversation_id, settings)
    except Exception as e:  # noqa: BLE001 — background best-effort
        log.warning("memory.summarize.failed", conversation_id=conversation_id, error=str(e))


async def _run(conversation_id: str, settings: Any) -> None:
    latest = await store.get_latest_episode(conversation_id)
    from_seq = (latest.to_seq + 1) if latest else 0

    messages = await store.get_messages(conversation_id, from_seq=from_seq)
    if len(messages) < SUMMARY_TRIGGER_THRESHOLD:
        return

    # Fold everything except the tail into a summary; leave the tail raw so the
    # next turn still gets fine-grained recent context via the DB history.
    fold = messages[:-KEEP_TAIL] if len(messages) > KEEP_TAIL else messages
    if not fold:
        return

    prior_summary = latest.summary if latest else None
    transcript = _render_transcript(fold)

    prompt = _build_prompt(prior_summary, transcript)
    client = Anthropic(api_key=settings.anthropic_api_key)
    response = await asyncio.to_thread(
        client.messages.create,
        model=settings.anthropic_model,
        max_tokens=SUMMARY_MAX_TOKENS,
        temperature=0.0,
        system=SUMMARY_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    text_blocks = [b.text for b in response.content if b.type == "text"]
    summary = ("\n".join(text_blocks)).strip()
    if not summary:
        return

    await store.add_episode(
        conversation_id=conversation_id,
        from_seq=fold[0].seq,
        to_seq=fold[-1].seq,
        summary=summary,
    )
    log.info(
        "memory.summarize.written",
        conversation_id=conversation_id,
        from_seq=fold[0].seq,
        to_seq=fold[-1].seq,
        chars=len(summary),
    )


SUMMARY_SYSTEM = (
    "You are a memory compaction assistant. Given prior turns of a chat, write "
    "a terse third-person summary (< 200 words) capturing: the user's goals so "
    "far, key decisions made, key numeric results already computed (with the "
    "metric name), and any explicit preferences the user has stated. Bullet "
    "points OK. Do NOT invent facts — only summarise what is present."
)


def _build_prompt(prior_summary: str | None, transcript: str) -> str:
    parts: list[str] = []
    if prior_summary:
        parts.append("Existing summary of even earlier turns (preserve accurate details):")
        parts.append(prior_summary)
        parts.append("")
    parts.append("New turns to fold in:")
    parts.append(transcript)
    parts.append("")
    parts.append("Return only the updated summary text.")
    return "\n".join(parts)


def _render_transcript(messages: list[store.MessageRow]) -> str:
    lines: list[str] = []
    for m in messages:
        text = _content_to_text(m.content)
        if not text.strip():
            continue
        lines.append(f"[{m.role} #{m.seq}] {text}")
    return "\n".join(lines)


def _content_to_text(content: list[dict[str, Any]]) -> str:
    """Flatten Anthropic content blocks down to a plain-text summary line."""
    parts: list[str] = []
    for block in content:
        t = block.get("type")
        if t == "text":
            parts.append(str(block.get("text", "")))
        elif t == "tool_use":
            parts.append(
                f"[tool_use:{block.get('name')}] {json.dumps(block.get('input') or {}, default=str)[:200]}",
            )
        elif t == "tool_result":
            body = block.get("content")
            if isinstance(body, list):
                inner = " ".join(
                    b.get("text", "") for b in body if isinstance(b, dict)
                )
            else:
                inner = str(body)
            parts.append(f"[tool_result] {inner[:200]}")
    return " ".join(parts)
