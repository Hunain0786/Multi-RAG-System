"""`query_postgres` agent tool — read-only SELECT escape hatch."""

from __future__ import annotations

import re
from typing import Any

NAME = "query_postgres"

TOOL_SCHEMA: dict[str, Any] = {
    "name": NAME,
    "description": (
        "Read-only SELECT escape hatch against the operational Postgres. "
        "Use ONLY when the semantic registry cannot express the question. "
        "Rejected: INSERT/UPDATE/DELETE/DROP/ALTER/TRUNCATE/CREATE/GRANT/REVOKE/COPY. "
        "The result is automatically capped at 100 rows."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "sql": {"type": "string"},
        },
        "required": ["sql"],
    },
}

_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|"
    r"vacuum|analyze|refresh|do|comment)\b",
    re.IGNORECASE,
)
_STARTS_WITH_SELECT_OR_WITH = re.compile(r"^\s*(select|with)\b", re.IGNORECASE)
_HAS_LIMIT = re.compile(r"\blimit\s+\d+", re.IGNORECASE)


def _validate(sql: str) -> str:
    stripped = sql.strip().rstrip(";")
    if not _STARTS_WITH_SELECT_OR_WITH.search(stripped):
        raise ValueError("query_postgres accepts only SELECT / WITH statements")
    if ";" in stripped:
        raise ValueError("query_postgres does not accept multi-statement input")
    if _FORBIDDEN.search(stripped):
        raise ValueError("query_postgres blocked a forbidden keyword")
    if not _HAS_LIMIT.search(stripped):
        stripped = stripped + " LIMIT 100"
    return stripped


async def run(input_: dict[str, Any]) -> dict[str, Any]:
    from psycopg.rows import dict_row

    from multirag.db.pool import fetch_conn
    from multirag.semantic.compile import _normalise_row

    sql = _validate(input_["sql"])
    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(sql)
            rows = await cur.fetchall()

    normalised = [_normalise_row(r) for r in rows]
    return {
        "sql": sql,
        "row_count": len(normalised),
        "rows": normalised[:100],
    }
