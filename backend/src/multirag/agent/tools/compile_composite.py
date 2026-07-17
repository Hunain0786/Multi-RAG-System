"""`compile_composite` agent tool — many non-grouped metrics in one SQL scan."""

from __future__ import annotations

from typing import Any

from multirag.semantic.compile import compile_composite, run_compiled

NAME = "compile_composite"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Compute MULTIPLE registered metrics of the SAME domain in a SINGLE SQL scan. "
        "Use when the user asks for several non-grouped KPIs over the same filter window. "
        "All metric names must belong to the same domain — this tool cannot cross domains. "
        "Cannot GROUP BY dimensions; use compile_metric for grouped output."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "metrics": {
                "type": "array",
                "description": "List of {alias, metric} objects (all same domain).",
                "items": {
                    "type": "object",
                    "properties": {
                        "alias": {"type": "string"},
                        "metric": {"type": "string"},
                    },
                    "required": ["alias", "metric"],
                },
                "minItems": 1,
            },
            "filters": {"type": "object"},
        },
        "required": ["metrics"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    q = compile_composite(metrics=input_["metrics"], filters=input_.get("filters"))
    rows = await run_compiled(q)
    row = rows[0] if rows else {c.name: None for c in q.columns}
    return {
        "domain": q.domain.name,
        "columns": [
            {"name": c.name, "label": c.label, "format": c.format} for c in q.columns
        ],
        "row": row,
        "sql": q.sql,
    }
