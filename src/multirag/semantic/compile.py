"""Compile a namespaced metric request into parameterised SQL.

Same signature and result shape as the Crizac reference `compile.py`, but
multi-domain aware. The LLM only ever picks:

    (metric_name='<domain>.<metric>', dimensions=[...], filters={...}, order_by, limit, offset)

and we assemble the SQL — the LLM never touches column names.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from multirag.semantic.filters import build_ops_filter_clauses, resolve_ops_filters
from multirag.semantic.registry import (
    DOMAINS,
    dimension_names,
    find_dimension,
    find_metric,
    metric_names,
)
from multirag.semantic.registry.base import DimensionDef, DomainDef, MetricDef

DEFAULT_LIMIT = 50
MAX_LIMIT = 500


@dataclass
class CompiledColumn:
    name: str
    label: str
    format: str  # MetricFormat | "string"


@dataclass
class CompiledQuery:
    sql: str
    params: list[Any]
    columns: list[CompiledColumn]
    metric: MetricDef
    domain: DomainDef
    dimensions: list[DimensionDef]
    limit: int
    offset: int


@dataclass
class CompiledComposite:
    sql: str
    params: list[Any]
    columns: list[CompiledColumn]
    domain: DomainDef


# ---------------------------------------------------------------------------
# compile_metric
# ---------------------------------------------------------------------------

def compile_metric(
    metric_name: str,
    dimensions: list[str] | None = None,
    filters: dict[str, Any] | None = None,
    order_by: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> CompiledQuery:
    hit = find_metric(metric_name)
    if not hit:
        raise ValueError(
            f'Unknown metric "{metric_name}". Valid metrics: {", ".join(metric_names())}'
        )
    domain, metric = hit

    dim_names = dimensions or []
    dims: list[DimensionDef] = []
    for n in dim_names:
        d = find_dimension(domain.name, n)
        if not d:
            raise ValueError(
                f'Unknown dimension "{n}" for domain "{domain.name}". '
                f"Valid dimensions: {', '.join(dimension_names(domain.name))}"
            )
        dims.append(d)

    ops = resolve_ops_filters(filters)
    ops_where, params, filter_joins = build_ops_filter_clauses(ops, domain)

    # Collect all required joins: dimension joins + metric join + filter joins.
    required_joins: set[str] = set(filter_joins)
    for d in dims:
        required_joins.update(d.required_joins)
    required_joins.update(metric.required_joins)

    # Validate joins exist on the domain.
    for j in required_joins:
        if j not in domain.joins:
            raise ValueError(
                f'domain "{domain.name}" has no join alias "{j}" '
                f"(available: {sorted(domain.joins)})"
            )

    # Assemble WHERE
    where_parts: list[str] = []
    if ops_where and ops_where != "TRUE":
        where_parts.append(f"({ops_where})")
    if metric.filter:
        where_parts.append(f"({metric.filter})")
    where_clause = " AND ".join(where_parts) if where_parts else "TRUE"

    # Assemble SELECT columns
    select_clauses: list[str] = []
    group_by_ordinals: list[int] = []
    columns: list[CompiledColumn] = []
    for i, d in enumerate(dims):
        alias = f"dim_{i + 1}"
        select_clauses.append(f"{d.expr} AS {alias}")
        group_by_ordinals.append(i + 1)
        columns.append(CompiledColumn(name=alias, label=d.label, format="string"))
    select_clauses.append(f"{metric.expr} AS value")
    columns.append(CompiledColumn(name="value", label=metric.label, format=metric.format))

    # ORDER BY
    order_mode = order_by or ("metric_desc" if dims else None)
    order_sql = ""
    if order_mode == "metric_desc":
        order_sql = "ORDER BY value DESC NULLS LAST"
    elif order_mode == "metric_asc":
        order_sql = "ORDER BY value ASC NULLS LAST"
    elif order_mode == "dim_asc" and dims:
        order_sql = "ORDER BY " + ", ".join(f"{n} ASC" for n in group_by_ordinals)

    row_limit = max(1, min(limit or DEFAULT_LIMIT, MAX_LIMIT))
    row_offset = max(0, offset or 0)
    if row_offset > 0 and not order_sql:
        order_sql = "ORDER BY value DESC NULLS LAST"

    # FROM + JOINs (stable alphabetical order of join aliases)
    from_parts = [f"FROM {domain.fact_table} {domain.fact_alias}"]
    for alias in sorted(required_joins):
        from_parts.append(domain.joins[alias])

    parts = [
        f"SELECT {', '.join(select_clauses)}",
        "\n".join(from_parts),
        f"WHERE {where_clause}",
    ]
    if group_by_ordinals:
        parts.append(f"GROUP BY {', '.join(str(n) for n in group_by_ordinals)}")
    if order_sql:
        parts.append(order_sql)
    parts.append(f"LIMIT {row_limit}")
    if row_offset > 0:
        parts.append(f"OFFSET {row_offset}")

    return CompiledQuery(
        sql="\n".join(parts),
        params=params,
        columns=columns,
        metric=metric,
        domain=domain,
        dimensions=dims,
        limit=row_limit,
        offset=row_offset,
    )


# ---------------------------------------------------------------------------
# compile_composite — several metrics of the SAME domain in one scan
# ---------------------------------------------------------------------------

def compile_composite(
    metrics: list[dict[str, str]],
    filters: dict[str, Any] | None = None,
) -> CompiledComposite:
    """Compute multiple non-grouped metrics from the same domain in one pass.

    `metrics` is a list of `{"alias": "<col_alias>", "metric": "<domain>.<name>"}`.
    All metrics MUST belong to the same domain (compiler enforces this).
    """
    if not metrics:
        raise ValueError("compile_composite requires at least one metric")

    resolved: list[tuple[str, DomainDef, MetricDef]] = []
    for entry in metrics:
        alias = entry["alias"]
        name = entry["metric"]
        hit = find_metric(name)
        if not hit:
            raise ValueError(
                f'Unknown metric "{name}". Valid metrics: {", ".join(metric_names())}'
            )
        d, m = hit
        if m.filter:
            raise ValueError(
                f'compile_composite: metric "{name}" carries a per-metric filter '
                f"({m.filter}) and can't be composed. Call compile_metric for that "
                f"one in isolation."
            )
        resolved.append((alias, d, m))

    domain = resolved[0][1]
    for alias, d, m in resolved:
        if d.name != domain.name:
            raise ValueError(
                f'compile_composite: metric "{d.name}.{m.name}" belongs to domain '
                f'"{d.name}" but the composite is scoped to "{domain.name}". '
                f"Composite queries cannot cross domains."
            )

    ops = resolve_ops_filters(filters)
    ops_where, params, filter_joins = build_ops_filter_clauses(ops, domain)

    required_joins: set[str] = set(filter_joins)
    for _, _, m in resolved:
        required_joins.update(m.required_joins)

    select_clauses: list[str] = []
    columns: list[CompiledColumn] = []
    for alias, _, m in resolved:
        select_clauses.append(f"{m.expr} AS {alias}")
        columns.append(CompiledColumn(name=alias, label=m.label, format=m.format))

    from_parts = [f"FROM {domain.fact_table} {domain.fact_alias}"]
    for alias in sorted(required_joins):
        from_parts.append(domain.joins[alias])

    where_clause = ops_where or "TRUE"

    sql = "\n".join(
        [
            f"SELECT {', '.join(select_clauses)}",
            "\n".join(from_parts),
            f"WHERE {where_clause}",
        ]
    )

    return CompiledComposite(sql=sql, params=params, columns=columns, domain=domain)


# ---------------------------------------------------------------------------
# Convenience: run a compiled query against the pool
# ---------------------------------------------------------------------------

async def run_compiled(query: CompiledQuery | CompiledComposite) -> list[dict[str, Any]]:
    """Execute a compiled query. Returns a list of dict rows."""
    from psycopg.rows import dict_row

    from multirag.db.pool import fetch_conn

    async with fetch_conn() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query.sql, query.params)
            rows = await cur.fetchall()

    # Ensure numeric/date types are JSON-serialisable for the tool result.
    return [_normalise_row(r) for r in rows]


def _normalise_row(row: dict[str, Any]) -> dict[str, Any]:
    from datetime import date, datetime
    from decimal import Decimal

    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, Decimal):
            out[k] = float(v)
        elif isinstance(v, (datetime, date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


__all__ = [
    "CompiledColumn",
    "CompiledComposite",
    "CompiledQuery",
    "compile_composite",
    "compile_metric",
    "run_compiled",
]
