"""Anthropic Messages API multi-turn tool_use loop.

Yields structured events (dict) instead of streaming raw Anthropic events so the
FastAPI SSE endpoint can render them consistently. Parallel tool_use blocks in a
single turn are executed concurrently.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

from anthropic import Anthropic

from multirag.agent.prompts.system import SYSTEM_PROMPT
from multirag.agent.tools import TOOL_RUNNERS, TOOL_SCHEMAS
from multirag.config import get_settings
from multirag.logging import get_logger

log = get_logger(__name__)

MAX_STEPS = 10


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


async def run_agent(messages: list[ChatMessage]) -> AsyncIterator[dict[str, Any]]:
    """Yield events: {type: 'text'|'tool_use'|'tool_result'|'stop'|'error', ...}.

    Caller is responsible for accumulating text for the UI. Messages may include
    prior turns (history). The system prompt is added automatically.
    """
    settings = get_settings()
    if not settings.anthropic_api_key:
        yield {"type": "error", "message": "ANTHROPIC_API_KEY is not set"}
        return

    client = Anthropic(api_key=settings.anthropic_api_key)
    history: list[dict[str, Any]] = list(messages)

    for step in range(MAX_STEPS):
        response = await asyncio.to_thread(
            client.messages.create,
            model=settings.anthropic_model,
            max_tokens=settings.anthropic_max_tokens,
            temperature=settings.anthropic_temperature,
            system=SYSTEM_PROMPT,
            tools=TOOL_SCHEMAS,
            messages=history,
        )

        assistant_content: list[dict[str, Any]] = []
        tool_uses: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
                yield {"type": "text", "text": block.text}
            elif block.type == "tool_use":
                tu = {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }
                assistant_content.append(tu)
                tool_uses.append(tu)
                yield {
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                }

        history.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason != "tool_use" or not tool_uses:
            yield {"type": "stop", "reason": response.stop_reason, "step": step}
            return

        # Run tool_use blocks concurrently.
        results = await asyncio.gather(
            *[_run_tool(t["name"], t["input"] or {}, t["id"]) for t in tool_uses]
        )
        for tu, res in zip(tool_uses, results, strict=True):
            body = json.loads(res["content"][0]["text"]) if not res.get("is_error") else res["content"][0]["text"]
            yield {
                "type": "tool_result",
                "tool_use_id": tu["id"],
                "name": tu["name"],
                "is_error": bool(res.get("is_error")),
                "result": body,
            }

        history.append({"role": "user", "content": results})

    yield {"type": "error", "message": f"agent exceeded MAX_STEPS={MAX_STEPS}"}
