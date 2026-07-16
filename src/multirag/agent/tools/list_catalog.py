"""`list_catalog` agent tool — dump the compact registry catalog."""

from __future__ import annotations

from typing import Any

from multirag.semantic.registry import compact_catalog

NAME = "list_catalog"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Return the compact catalog of every domain, metric, and dimension in the "
        "semantic-layer registry. Free + deterministic. Call once early in a session "
        "if you're not sure what's defined."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


async def run(input_: dict[str, Any]) -> dict[str, str]:
    return {"catalog": compact_catalog()}
