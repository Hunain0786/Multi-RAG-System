"""OpenAI Chat Completions multi-turn tool-calling loop with durable memory.

Yields structured events (dict) instead of streaming raw provider events so the
FastAPI SSE endpoint can render them consistently. Parallel tool calls in a
single turn are executed concurrently.

Messages are stored and emitted as content blocks (text / tool_use /
tool_result); `agent.openai_compat` translates to and from the Chat Completions
shape at the API boundary.

Memory contract:
- If `conversation_id` is None, we create one and yield `{type:"conversation", id}`
  as the first event so the frontend can capture it and reuse it on the next turn.
- Postgres is the source of truth for message history. The frontend may send a
  full `messages` array for its own state, but we only consume the LAST entry
  (must be role='user') and re-hydrate the preceding history from the DB.
- Each new assistant response / tool_result batch is persisted incrementally
  as it arrives, so if the client disconnects we don't lose the partial turn.
- On `stop`, we optionally kick off a summariser (see `config.memory_auto_summarize`).
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from typing import Any, AsyncIterator

from openai import OpenAI

from multirag.agent.context import reset_conversation_id, set_conversation_id
from multirag.agent.openai_compat import (
    from_openai_message,
    to_openai_messages,
    to_openai_tools,
)
from multirag.agent.prompts.system import SYSTEM_PROMPT
from multirag.agent.tools import TOOL_RUNNERS, TOOL_SCHEMAS
from multirag.config import get_settings
from multirag.logging import get_logger
from multirag.memory import recall as memory_recall
from multirag.memory import store as memory_store
from multirag.memory.summarize import maybe_summarize

log = get_logger(__name__)

MAX_STEPS = 10
TITLE_MAX_LEN = 60

OPENAI_TOOLS = to_openai_tools(TOOL_SCHEMAS)


class ChatMessage(dict):
    """Loose shape: {'role': 'user'|'assistant', 'content': str | list[dict]}."""


async def _run_tool(name: str, tool_input: dict[str, Any], tool_use_id: str) -> dict[str, Any]:
    runner = TOOL_RUNNERS.get(name)
    if runner is None:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "is_error": True,
            "content": [{"type": "text", "text": f"unknown tool: {name}"}],
        }
    try:
        result = await runner(tool_input or {})
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": [{"type": "text", "text": json.dumps(result, default=str)}],
        }
    except Exception as e:  # noqa: BLE001 — tool errors go back to the LLM as messages
        log.warning("tool.error", name=name, error=str(e))
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "is_error": True,
            "content": [{"type": "text", "text": f"{type(e).__name__}: {e}"}],
        }


def _content_to_blocks(content: Any) -> list[dict[str, Any]]:
    """Normalise an inbound message's `content` to a block list."""
    if isinstance(content, list):
        return content
    return [{"type": "text", "text": str(content or "")}]


def _first_text(content: list[dict[str, Any]]) -> str:
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            return str(block.get("text") or "")
    return ""


async def run_agent(
    messages: list[ChatMessage],
    conversation_id: str | None = None,
) -> AsyncIterator[dict[str, Any]]:
    """Yield events: 'conversation' | 'text' | 'tool_use' | 'tool_result' | 'stop' | 'error'.

    `messages` must be non-empty and the LAST item must be role='user'. Preceding
    items are ignored; DB history is authoritative.
    """
    settings = get_settings()
    if not settings.openai_api_key:
        yield {"type": "error", "message": "OPENAI_API_KEY is not set"}
        return

    if not messages or messages[-1].get("role") != "user":
        yield {"type": "error", "message": "messages must be non-empty and end with role='user'"}
        return

    new_user_content = _content_to_blocks(messages[-1].get("content"))
    new_user_text = _first_text(new_user_content)

    # ------------------------------------------------------------------
    # Ensure a conversation exists and load its authoritative history.
    # ------------------------------------------------------------------
    created_new = False
    if not conversation_id:
        conversation_id = await memory_store.create_conversation(
            user_id=settings.memory_user_id,
            title=None,
        )
        created_new = True
    else:
        existing = await memory_store.get_conversation(conversation_id)
        if existing is None:
            # Client sent a stale id — create a fresh one and let them know.
            conversation_id = await memory_store.create_conversation(
                user_id=settings.memory_user_id,
                title=None,
            )
            created_new = True

    yield {"type": "conversation", "id": conversation_id, "created": created_new}

    # Set the title on first turn (best-effort).
    if new_user_text.strip():
        title = textwrap.shorten(
            new_user_text.strip(), width=TITLE_MAX_LEN, placeholder="…",
        )
        await memory_store.set_conversation_title(conversation_id, title)

    # Persist the new user message.
    await memory_store.append_message(
        conversation_id=conversation_id,
        role="user",
        content=new_user_content,
    )

    # Rebuild history. `get_messages` returns everything up to and including
    # the freshly-persisted user turn.
    history_rows = await memory_store.get_messages(conversation_id)
    history: list[dict[str, Any]] = [
        {"role": r.role, "content": r.content} for r in history_rows
    ]

    # ------------------------------------------------------------------
    # Assemble system prompt (base + optional memory context).
    # ------------------------------------------------------------------
    memory_ctx = await memory_recall.build_memory_context(
        query=new_user_text,
        conversation_id=conversation_id,
        user_id=settings.memory_user_id,
        top_k=settings.memory_recall_top_k,
    )
    system_prompt = SYSTEM_PROMPT if not memory_ctx else f"{SYSTEM_PROMPT}\n\n{memory_ctx}"

    client = OpenAI(api_key=settings.openai_api_key)
    ctx_token = set_conversation_id(conversation_id)
    try:
        for step in range(MAX_STEPS):
            response = await asyncio.to_thread(
                client.chat.completions.create,
                model=settings.openai_model,
                max_completion_tokens=settings.openai_max_tokens,
                temperature=settings.openai_temperature,
                tools=OPENAI_TOOLS,
                messages=to_openai_messages(system_prompt, history),
            )

            choice = response.choices[0]
            assistant_content = from_openai_message(choice.message)
            tool_uses: list[dict[str, Any]] = []

            for block in assistant_content:
                if block["type"] == "text":
                    yield {"type": "text", "text": block["text"]}
                else:
                    tool_uses.append(block)
                    yield dict(block)

            history.append({"role": "assistant", "content": assistant_content})
            await memory_store.append_message(
                conversation_id=conversation_id,
                role="assistant",
                content=assistant_content,
            )

            if choice.finish_reason != "tool_calls" or not tool_uses:
                yield {"type": "stop", "reason": choice.finish_reason, "step": step}
                # Fire-and-forget rolling summary (no-op when disabled).
                asyncio.create_task(maybe_summarize(conversation_id))
                return

            # Run tool_use blocks concurrently.
            results = await asyncio.gather(
                *[_run_tool(t["name"], t["input"] or {}, t["id"]) for t in tool_uses],
            )
            for tu, res in zip(tool_uses, results, strict=True):
                body = (
                    json.loads(res["content"][0]["text"])
                    if not res.get("is_error")
                    else res["content"][0]["text"]
                )
                yield {
                    "type": "tool_result",
                    "tool_use_id": tu["id"],
                    "name": tu["name"],
                    "is_error": bool(res.get("is_error")),
                    "result": body,
                }

            history.append({"role": "user", "content": results})
            await memory_store.append_message(
                conversation_id=conversation_id,
                role="user",
                content=results,
            )

        yield {"type": "error", "message": f"agent exceeded MAX_STEPS={MAX_STEPS}"}
    finally:
        reset_conversation_id(ctx_token)
