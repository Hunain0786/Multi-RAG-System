"""Every metric/dimension registered should pass validation and be findable."""

from __future__ import annotations

import pytest

from multirag.semantic.registry import (
    DOMAINS,
    dimension_names,
    find_dimension,
    find_metric,
    metric_names,
)


def test_domains_are_registered():
    assert set(DOMAINS.keys()) == {"sales", "inventory", "hr", "finance"}


def test_metric_names_are_namespaced():
    names = metric_names()
    assert all("." in n for n in names)
    assert "sales.revenue_total" in names
    assert "inventory.low_stock_products" in names
    assert "hr.headcount" in names
    assert "finance.failure_rate_pct" in names


def test_find_metric_returns_domain_and_metric():
    hit = find_metric("sales.revenue_total")
    assert hit is not None
    domain, metric = hit
    assert domain.name == "sales"
    assert metric.name == "revenue_total"
    assert metric.expr
    assert metric.description


def test_find_metric_unknown_returns_none():
    assert find_metric("nope.does_not_exist") is None
    assert find_metric("bareword") is None


@pytest.mark.parametrize("domain, dim", [
    ("sales", "product_category"),
    ("sales", "order_month"),
    ("inventory", "warehouse"),
    ("hr", "department"),
    ("finance", "method"),
])
def test_dimensions_exist(domain: str, dim: str):
    assert find_dimension(domain, dim) is not None


def test_dimension_names_per_domain():
    assert "product_category" in dimension_names("sales")
    assert "warehouse" in dimension_names("inventory")
    assert dimension_names("bogus") == []


def test_all_required_joins_declared():
    """Every dimension.required_joins alias must exist in its domain.joins."""
    for name, d in DOMAINS.items():
        declared = set(d.joins.keys())
        for dim in d.dimensions:
            for j in dim.required_joins:
                assert j in declared, f"{name}.{dim.name} needs join '{j}' which isn't declared"
        for m in d.metrics:
            for j in m.required_joins:
                assert j in declared, f"{name}.{m.name} needs join '{j}' which isn't declared"
