"""Golden-string tests for the compiled SQL.

We assert the shape (SELECT, FROM, JOINs, WHERE, GROUP BY, ORDER BY, LIMIT)
rather than an exact whitespace match, so small formatting tweaks don't break
tests but structural regressions do.
"""

from __future__ import annotations

import pytest

from multirag.semantic.compile import compile_composite, compile_metric


def test_simple_metric_no_dims_no_joins():
    q = compile_metric("sales.orders_count")
    sql = q.sql
    assert "FROM orders o" in sql
    assert "SELECT" in sql
    assert "AS value" in sql
    assert "GROUP BY" not in sql
    assert "LIMIT 50" in sql
    assert q.params == []


def test_metric_with_customer_dim_joins_customers():
    q = compile_metric(
        "sales.revenue_total",
        dimensions=["customer_country"],
    )
    assert "LEFT JOIN customers c ON c.id = o.customer_id" in q.sql
    assert "GROUP BY 1" in q.sql
    assert "ORDER BY value DESC NULLS LAST" in q.sql
    assert "c.country" in q.sql


def test_metric_with_product_dim_joins_order_items_and_products():
    q = compile_metric("sales.units_sold", dimensions=["product_category"])
    assert "LEFT JOIN order_items oi ON oi.order_id = o.id" in q.sql
    assert "LEFT JOIN products p ON p.id = oi.product_id" in q.sql
    assert "p.category" in q.sql


def test_metric_units_sold_requires_oi_even_without_dims():
    """units_sold declares required_joins=('oi',) so joining should be automatic."""
    q = compile_metric("sales.units_sold")
    assert "LEFT JOIN order_items oi" in q.sql


def test_ops_filters_period_last_30d_binds_two_params():
    q = compile_metric(
        "sales.revenue_total",
        filters={"period": "last_30d"},
    )
    assert "o.created_at >= %s" in q.sql
    assert "o.created_at < %s" in q.sql
    assert len(q.params) == 2


def test_ops_filters_country_requires_customers_join():
    q = compile_metric(
        "sales.revenue_total",
        filters={"country": ["US", "GB"]},
    )
    assert "LEFT JOIN customers c" in q.sql
    assert "c.country IN (%s, %s)" in q.sql
    assert "US" in q.params
    assert "GB" in q.params


def test_hr_metric_filters_on_hired_at():
    q = compile_metric(
        "hr.new_hires",
        dimensions=["department"],
        filters={"period": "q1_2026"},
    )
    assert "FROM employees e" in q.sql
    assert "e.hired_at >= %s" in q.sql
    assert "e.hired_at < %s" in q.sql
    assert "e.department" in q.sql


def test_inventory_ignores_period_filter():
    q = compile_metric(
        "inventory.low_stock_products",
        dimensions=["product_category"],
        filters={"period": "last_30d"},
    )
    # inventory has no time_column, so no time filter clause is emitted
    assert "i.updated_at" not in q.sql
    assert q.params == []


def test_pagination_offset_forces_order_by():
    q = compile_metric("sales.revenue_total", offset=50)
    assert "ORDER BY value DESC" in q.sql
    assert "OFFSET 50" in q.sql


def test_limit_capped_at_max():
    q = compile_metric("sales.revenue_total", limit=99_999)
    assert "LIMIT 500" in q.sql


def test_unknown_metric_raises():
    with pytest.raises(ValueError, match="Unknown metric"):
        compile_metric("nope.bogus")


def test_unknown_dimension_raises():
    with pytest.raises(ValueError, match="Unknown dimension"):
        compile_metric("sales.orders_count", dimensions=["nonsense"])


def test_composite_same_domain_ok():
    q = compile_composite(
        metrics=[
            {"alias": "orders", "metric": "sales.orders_count"},
            {"alias": "rev", "metric": "sales.revenue_total"},
        ],
        filters={"period": "q1_2026"},
    )
    assert "orders" in q.sql and "rev" in q.sql
    assert "FROM orders o" in q.sql


def test_composite_cross_domain_rejects():
    with pytest.raises(ValueError, match="cannot cross domains"):
        compile_composite(
            metrics=[
                {"alias": "a", "metric": "sales.orders_count"},
                {"alias": "b", "metric": "hr.headcount"},
            ],
        )
