"""Period grammar + filter compilation."""

from __future__ import annotations

from datetime import date, datetime, timezone

import pytest

from multirag.semantic.filters import (
    OpsFilters,
    _resolve_period,
    build_ops_filter_clauses,
    resolve_ops_filters,
)
from multirag.semantic.registry.sales import DOMAIN as SALES

NOW = datetime(2026, 5, 15, tzinfo=timezone.utc)


@pytest.mark.parametrize("period, expected", [
    ("all", None),
    ("last_7d", (date(2026, 5, 8), date(2026, 5, 16))),
    ("last_30d", (date(2026, 4, 15), date(2026, 5, 16))),
    ("ytd", (date(2026, 1, 1), date(2027, 1, 1))),
    ("mtd", (date(2026, 5, 1), date(2026, 5, 16))),
    ("qtd", (date(2026, 4, 1), date(2026, 5, 16))),
    ("q1_2026", (date(2026, 1, 1), date(2026, 4, 1))),
    ("q4_2026", (date(2026, 10, 1), date(2027, 1, 1))),
    ("fy25-26", (date(2025, 4, 1), date(2026, 4, 1))),
    ("2025", (date(2025, 1, 1), date(2026, 1, 1))),
    ("2024-2025", (date(2024, 1, 1), date(2026, 1, 1))),
    ("2026-03", (date(2026, 3, 1), date(2026, 4, 1))),
    ("bogus_period", None),
])
def test_period_resolution(period: str, expected):
    assert _resolve_period(period, now=NOW) == expected


def test_resolve_ops_filters_accepts_short_and_long_keys():
    ops = resolve_ops_filters({"from": "2026-01-01", "country": "US"})
    assert ops.from_date == "2026-01-01"
    assert ops.country == ["US"]


def test_build_ops_filter_clauses_ignores_unsupported_keys():
    ops = OpsFilters(period="all", warehouse_id="wh_0001")
    sql, params, joins = build_ops_filter_clauses(ops, SALES)
    # sales domain does NOT support warehouse_id
    assert "warehouse" not in sql
    assert params == []
    assert joins == set()


def test_country_filter_emits_customers_join():
    ops = OpsFilters(country=["US", "GB"])
    sql, params, joins = build_ops_filter_clauses(ops, SALES, now=NOW)
    assert "c.country IN" in sql
    assert params == ["US", "GB"]
    assert joins == {"c"}


def test_from_to_dates_override_period():
    ops = OpsFilters(period="all", from_date="2026-01-01", to_date="2026-02-01")
    sql, params, _ = build_ops_filter_clauses(ops, SALES, now=NOW)
    assert "o.created_at >= %s" in sql
    assert "o.created_at < %s" in sql
    assert params == [date(2026, 1, 1), date(2026, 2, 1)]
