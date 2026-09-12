"""Translation between the stored content-block format and the OpenAI Chat API.

Messages are persisted in Postgres — and streamed to the frontend — as a list
of content blocks:

    text        : {"type": "text", "text": ...}
    tool_use    : {"type": "tool_use", "id": ..., "name": ..., "input": {...}}
    tool_result : {"type": "tool_result", "tool_use_id": ..., "content": ..., "is_error": ...}

That block shape is the storage and wire contract, so the provider swap is
confined to this module: the tool registry, `memory.store`, the SSE event
payloads and the frontend all keep working unchanged, and conversations written
before the swap replay without a migration.

The asymmetry worth knowing: a stored message with role='user' may carry
`tool_result` blocks, which OpenAI models as separate messages with role='tool'.
One stored row can therefore expand into several Chat Completions messages.
"""

from __future__ import annotations

import json
from typing import Any

from multirag.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

def to_openai_tools(schemas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Wrap the registry's `{name, description, input_schema}` tool schemas."""
    return [
        {
            "type": "function",
            "function": {
                "name": schema["name"],
                "description": schema.get("description", ""),
                "parameters": schema.get("input_schema")
                or {"type": "object", "properties": {}},
            },
        }
        for schema in schemas
    ]


# ---------------------------------------------------------------------------
# Blocks -> OpenAI messages
# ---------------------------------------------------------------------------

def _blocks_to_text(blocks: list[dict[str, Any]]) -> str:
    return "\n".join(
        str(b.get("text") or "")
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "text"
    ).strip()


def _tool_result_text(block: dict[str, Any]) -> str:
    body = block.get("content")
    if isinstance(body, list):
        return "\n".join(
            str(b.get("text") or "") for b in body if isinstance(b, dict)
        ).strip()
    return "" if body is None else str(body)


def _assistant_message(blocks: list[dict[str, Any]]) -> dict[str, Any]:
    tool_calls = [
        {
            "id": b.get("id") or "",
            "type": "function",
            "function": {
                "name": b.get("name") or "",
                "arguments": json.dumps(b.get("input") or {}, default=str),
            },
        }
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "tool_use"
    ]
    text = _blocks_to_text(blocks)

    message: dict[str, Any] = {"role": "assistant"}
    if tool_calls:
        message["tool_calls"] = tool_calls
        # Content is omitted rather than sent empty when the turn was tools-only.
        if text:
            message["content"] = text
    else:
        message["content"] = text
    return message


def _user_messages(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [
        {
            "role": "tool",
            "tool_call_id": b.get("tool_use_id") or "",
            # A tool message with empty content is rejected, and an empty result
            # is still information the model needs.
            "content": _tool_result_text(b) or "(no output)",
        }
        for b in blocks
        if isinstance(b, dict) and b.get("type") == "tool_result"
    ]
    text = _blocks_to_text(blocks)
    if text or not messages:
        messages.append({"role": "user", "content": text})
    return messages


def to_openai_messages(
    system_prompt: str,
    history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten stored history into Chat Completions messages."""
    messages: list[dict[str, Any]] = [{"role": "system", "content": system_prompt}]
    for entry in history:
        content = entry.get("content")
        blocks = (
            content
            if isinstance(content, list)
            else [{"type": "text", "text": str(content or "")}]
        )
        if entry.get("role") == "assistant":
            messages.append(_assistant_message(blocks))
        else:
            messages.extend(_user_messages(blocks))
    return messages


# ---------------------------------------------------------------------------
# OpenAI response -> blocks
# ---------------------------------------------------------------------------

def _parse_arguments(raw: str | None, tool_name: str) -> dict[str, Any]:
    """Malformed arguments degrade to `{}` so the tool's own validation reports
    the problem back to the model as a tool_result instead of killing the turn."""
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        log.warning("openai.tool_arguments.unparseable", tool=tool_name, raw=raw[:200])
        return {}
    return parsed if isinstance(parsed, dict) else {}


def from_openai_message(message: Any) -> list[dict[str, Any]]:
    """Convert one assistant response into stored content blocks."""
    blocks: list[dict[str, Any]] = []
    if message.content:
        blocks.append({"type": "text", "text": message.content})
    for call in message.tool_calls or []:
        blocks.append(
            {
                "type": "tool_use",
                "id": call.id,
                "name": call.function.name,
                "input": _parse_arguments(call.function.arguments, call.function.name),
            },
        )
    return blocks
