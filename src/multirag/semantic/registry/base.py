"""Core primitives for the semantic layer: MetricDef, DimensionDef, ChartHint, DomainDef.

Mirrors the Crizac pattern (see reference `registry.py`) but adds `DomainDef` so we can
scope metrics/dimensions to a fact table with declarative joins to dimension tables.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

MetricFormat = Literal["integer", "percentage", "number", "days", "currency_usd", "string"]
TimeGrain = Literal["day", "week", "month", "quarter", "year"]
ChartType = Literal["bar", "line", "area", "pie", "table", "kpi"]


@dataclass(frozen=True)
class ChartHint:
    type: ChartType
    x_key: str | None = None
    y_keys: tuple[str, ...] = ("value",)


@dataclass(frozen=True)
class MetricDef:
    name: str
    label: str
    description: str
    expr: str
    format: MetricFormat
    chart_hint: ChartHint = field(default_factory=lambda: ChartHint(type="kpi"))
    reviewed_by: str = "multirag-team — 2026-07"
    example_use: str = ""
    filter: str | None = None  # optional per-metric WHERE clause (fact-alias qualified)
    required_joins: tuple[str, ...] = ()  # join aliases this metric's expr references


@dataclass(frozen=True)
class DimensionDef:
    name: str
    label: str
    description: str
    expr: str
    time_grain: TimeGrain | None = None
    required_joins: tuple[str, ...] = ()


@dataclass(frozen=True)
class DomainDef:
    """A registry scope with one fact table and a fixed set of joinable dim tables.

    `joins` maps a short alias (e.g. 'c' for customers) to the full JOIN clause
    the compiler will emit if any requested metric/dimension needs it. The compiler
    emits joins in lexical alias order for stable SQL.
    """

    name: str
    fact_table: str        # e.g. "orders"
    fact_alias: str        # e.g. "o"
    description: str
    joins: dict[str, str] = field(default_factory=dict)
    metrics: list[MetricDef] = field(default_factory=list)
    dimensions: list[DimensionDef] = field(default_factory=list)
    # Which OpsFilters keys this domain understands. Keys not listed are ignored
    # by the compiler for this domain.
    supported_filters: tuple[str, ...] = (
        "period",
        "from_date",
        "to_date",
        "country",
        "segment",
        "category",
        "status",
        "warehouse_id",
        "employee_id",
    )
    # Which fact-alias column the period/from/to filters apply to. Domains that
    # don't have a timestamp column (rare) can leave this None.
    time_column: str | None = None
