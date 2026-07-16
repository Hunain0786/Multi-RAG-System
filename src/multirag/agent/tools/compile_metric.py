"""`compile_metric` agent tool."""

from __future__ import annotations

from typing import Any

from multirag.semantic.compile import compile_metric, run_compiled

NAME = "compile_metric"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Compute a registered metric with optional GROUP BY dimensions and OpsFilters. "
        "PREFERRED for any numeric question that maps to metric + dimensions + period. "
        "Metric names are namespaced as '<domain>.<metric>' (e.g. 'sales.revenue_total', "
        "'inventory.low_stock_products', 'hr.headcount', 'finance.failure_rate_pct'). "
        "Call list_catalog first if you're not sure what's defined."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "metric": {
                "type": "string",
                "description": "Namespaced metric name, e.g. 'sales.revenue_total'.",
            },
            "dimensions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Dimension names to GROUP BY (order preserved).",
            },
            "filters": {
                "type": "object",
                "description": (
                    "OpsFilters: {period, from, to, country, segment, category, status, "
                    "warehouse_id, employee_id}. See system prompt for grammar."
                ),
            },
            "order_by": {
                "type": "string",
                "enum": ["metric_desc", "metric_asc", "dim_asc"],
                "description": "Sort mode; defaults to metric_desc when dimensions are present.",
            },
            "limit": {"type": "integer", "minimum": 1, "maximum": 500},
            "offset": {"type": "integer", "minimum": 0},
        },
        "required": ["metric"],
    },
}


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    q = compile_metric(
        metric_name=input_["metric"],
        dimensions=input_.get("dimensions"),
        filters=input_.get("filters"),
        order_by=input_.get("order_by"),
        limit=input_.get("limit"),
        offset=input_.get("offset"),
    )
    rows = await run_compiled(q)
    next_offset = q.offset + len(rows)
    has_more = len(rows) == q.limit
    return {
        "metric": f"{q.domain.name}.{q.metric.name}",
        "domain": q.domain.name,
        "columns": [
            {"name": c.name, "label": c.label, "format": c.format} for c in q.columns
        ],
        "rows": rows,
        "sql": q.sql,
        "chart_hint": {
            "type": q.metric.chart_hint.type,
            "x_key": q.metric.chart_hint.x_key,
        },
        "pagination": {
            "limit": q.limit,
            "offset": q.offset,
            "next_offset": next_offset,
            "has_more": has_more,
            "total_returned": len(rows),
        },
    }
