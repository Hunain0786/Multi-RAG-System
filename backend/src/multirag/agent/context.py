"""Per-request context accessible to tools (via contextvars).

The tool runner in `agent.loop` invokes a tool as `runner(input)`
with no side channel. Tools that need to know which conversation they belong to
(e.g. `remember` stamping `source_conversation_id`) pull it from here.

The loop sets and clears this in a try/finally so leaking across requests is
impossible.
"""

from __future__ import annotations

from contextvars import ContextVar

_CONV_ID: ContextVar[str | None] = ContextVar("multirag_conversation_id", default=None)


def current_conversation_id() -> str | None:
    return _CONV_ID.get()


def set_conversation_id(conv_id: str | None):
    return _CONV_ID.set(conv_id)


def reset_conversation_id(token) -> None:
    _CONV_ID.reset(token)
