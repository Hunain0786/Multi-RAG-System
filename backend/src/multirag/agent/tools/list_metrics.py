"""`list_metrics` agent tool — structured JSON with chart hints + examples."""

from __future__ import annotations

from typing import Any

from multirag.semantic.registry import list_metrics_catalog

NAME = "list_metrics"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Return a structured JSON list of all metrics with chart_hint, format, "
        "description, and example_use. Use when choosing a chart type or showing "
        "usage examples. Does NOT expose SQL."
    ),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    return {"metrics": list_metrics_catalog()}
