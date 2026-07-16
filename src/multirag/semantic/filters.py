"""Shared filter contract across all domains.

The LLM never writes raw WHERE clauses — it passes a dict of `OpsFilters` keys
which the compiler translates into parameterised SQL. Each domain declares which
subset it supports (see `DomainDef.supported_filters`); unsupported keys are
silently ignored so a filter dict can be reused across domains.

Period grammar (loose):
    'all'                    -> no time filter
    'last_7d' / 'last_30d' / 'last_90d' / 'last_365d'
    'ytd'                    -> from 2026-01-01
    'mtd'                    -> current month start
    'qtd'                    -> current quarter start
    'q1_2026' / 'q2_2026' ...
    'fy25-26' / 'fy24-25' ...  -> Indian FY (Apr-Mar)
    'YYYY-YYYY'              -> two calendar years, e.g. '2024-2025'
    'YYYY-MM'                -> month
    'YYYY'                   -> full year
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any


@dataclass
class OpsFilters:
    period: str = "all"
    from_date: date | str | None = None
    to_date: date | str | None = None
    country: list[str] | None = None
    segment: list[str] | None = None
    category: list[str] | None = None
    status: list[str] | None = None
    warehouse_id: str | None = None
    employee_id: str | None = None


def resolve_ops_filters(inp: dict[str, Any] | None) -> OpsFilters:
    if not inp:
        return OpsFilters()

    def _as_list(v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]

    return OpsFilters(
        period=inp.get("period", "all") or "all",
        from_date=inp.get("from") or inp.get("from_date"),
        to_date=inp.get("to") or inp.get("to_date"),
        country=_as_list(inp.get("country")),
        segment=_as_list(inp.get("segment")),
        category=_as_list(inp.get("category")),
        status=_as_list(inp.get("status")),
        warehouse_id=inp.get("warehouse_id") or inp.get("warehouseId"),
        employee_id=inp.get("employee_id") or inp.get("employeeId"),
    )


# ---------------------------------------------------------------------------
# Period resolution
# ---------------------------------------------------------------------------

_PERIOD_LAST_N_DAYS = re.compile(r"^last_(\d+)d$")
_PERIOD_Q = re.compile(r"^q([1-4])_(\d{4})$")
_PERIOD_FY = re.compile(r"^fy(\d{2})-(\d{2})$")
_PERIOD_YEAR = re.compile(r"^(\d{4})$")
_PERIOD_YEAR_RANGE = re.compile(r"^(\d{4})-(\d{4})$")
_PERIOD_MONTH = re.compile(r"^(\d{4})-(\d{2})$")


def _resolve_period(period: str, now: datetime | None = None) -> tuple[date, date] | None:
    """Return (from, to_exclusive) or None if period='all' / unknown."""
    if not period or period == "all":
        return None

    now = now or datetime.now(tz=timezone.utc)
    today = now.date()

    if m := _PERIOD_LAST_N_DAYS.match(period):
        days = int(m.group(1))
        return (date.fromordinal(today.toordinal() - days), date.fromordinal(today.toordinal() + 1))
    if period == "ytd":
        return (date(today.year, 1, 1), date(today.year + 1, 1, 1))
    if period == "mtd":
        return (date(today.year, today.month, 1), date.fromordinal(today.toordinal() + 1))
    if period == "qtd":
        q = (today.month - 1) // 3
        return (date(today.year, q * 3 + 1, 1), date.fromordinal(today.toordinal() + 1))
    if m := _PERIOD_Q.match(period):
        q, y = int(m.group(1)), int(m.group(2))
        start = date(y, (q - 1) * 3 + 1, 1)
        end_month = q * 3 + 1
        end = date(y + 1, 1, 1) if end_month == 13 else date(y, end_month, 1)
        return (start, end)
    if m := _PERIOD_FY.match(period):
        yy1, yy2 = int(m.group(1)), int(m.group(2))
        y1 = 2000 + yy1
        y2 = 2000 + yy2
        return (date(y1, 4, 1), date(y2, 4, 1))
    if m := _PERIOD_YEAR.match(period):
        y = int(m.group(1))
        return (date(y, 1, 1), date(y + 1, 1, 1))
    if m := _PERIOD_YEAR_RANGE.match(period):
        y1, y2 = int(m.group(1)), int(m.group(2))
        return (date(y1, 1, 1), date(y2 + 1, 1, 1))
    if m := _PERIOD_MONTH.match(period):
        y, mo = int(m.group(1)), int(m.group(2))
        next_month = date(y + 1, 1, 1) if mo == 12 else date(y, mo + 1, 1)
        return (date(y, mo, 1), next_month)

    return None


def _as_date(v: date | str | None) -> date | None:
    if v is None:
        return None
    if isinstance(v, date):
        return v
    return datetime.strptime(v, "%Y-%m-%d").date()


# ---------------------------------------------------------------------------
# Column resolution per domain
# ---------------------------------------------------------------------------

# Per-domain mapping: which SQL column each filter key targets. If a domain
# doesn't have a key, it's omitted here and the compiler silently drops it.
COLUMN_MAP: dict[str, dict[str, str]] = {
    "sales": {
        # time_column is domain-level; period/from/to use it
        "country": "c.country",         # joined customers
        "segment": "c.segment",
        "category": "p.category",       # joined via order_items -> products; sales domain omits
        "status": "o.status",
        "employee_id": "o.employee_id",
    },
    "inventory": {
        "category": "p.category",
        "warehouse_id": "i.warehouse_id",
    },
    "hr": {
        # tenure is time-based; period filter would be against hired_at
    },
    "finance": {
        "status": "t.status",
    },
}

# Per-domain: which joins each filter key requires (if any)
FILTER_JOIN_MAP: dict[str, dict[str, tuple[str, ...]]] = {
    "sales": {
        "country": ("c",),
        "segment": ("c",),
    },
    "inventory": {},
    "hr": {},
    "finance": {},
}


def build_ops_filter_clauses(
    ops: OpsFilters,
    domain: "DomainDef",  # forward-ref to avoid cycle at import time
    now: datetime | None = None,
) -> tuple[str, list[Any], set[str]]:
    """Compile `ops` into a WHERE clause fragment against `domain`.

    Returns (sql, params, extra_joins). `extra_joins` is the set of join aliases
    the compiler must include because a filter references them.
    """
    parts: list[str] = []
    params: list[Any] = []
    extra_joins: set[str] = set()
    supported = set(domain.supported_filters)
    cols = COLUMN_MAP.get(domain.name, {})
    join_reqs = FILTER_JOIN_MAP.get(domain.name, {})

    # ---- time filters ----
    if domain.time_column and "period" in supported:
        window = _resolve_period(ops.period, now=now)
        if window is not None:
            parts.append(f"{domain.time_column} >= %s AND {domain.time_column} < %s")
            params.extend([window[0], window[1]])
        else:
            fd = _as_date(ops.from_date)
            td = _as_date(ops.to_date)
            if fd is not None:
                parts.append(f"{domain.time_column} >= %s")
                params.append(fd)
            if td is not None:
                parts.append(f"{domain.time_column} < %s")
                params.append(td)

    # ---- scalar / IN filters ----
    def _in_filter(key: str, values: list[str] | None) -> None:
        if not values or key not in supported or key not in cols:
            return
        col = cols[key]
        placeholders = ", ".join(["%s"] * len(values))
        parts.append(f"{col} IN ({placeholders})")
        params.extend(values)
        extra_joins.update(join_reqs.get(key, ()))

    _in_filter("country", ops.country)
    _in_filter("segment", ops.segment)
    _in_filter("category", ops.category)
    _in_filter("status", ops.status)

    if ops.warehouse_id and "warehouse_id" in supported and "warehouse_id" in cols:
        parts.append(f"{cols['warehouse_id']} = %s")
        params.append(ops.warehouse_id)
        extra_joins.update(join_reqs.get("warehouse_id", ()))

    if ops.employee_id and "employee_id" in supported and "employee_id" in cols:
        parts.append(f"{cols['employee_id']} = %s")
        params.append(ops.employee_id)
        extra_joins.update(join_reqs.get("employee_id", ()))

    sql = " AND ".join(parts) if parts else "TRUE"
    return sql, params, extra_joins
