"""Sales domain — orders as the fact table.

Joins:
  c  -> customers  (order.customer_id  = c.id)
  e  -> employees  (order.employee_id  = e.id)
  oi -> order_items(oi.order_id        = o.id)
  p  -> products   (via oi.product_id  = p.id) — requires 'oi' to be joined first
"""

from __future__ import annotations

from multirag.semantic.registry.base import (
    ChartHint,
    DimensionDef,
    DomainDef,
    MetricDef,
)

_JOINS = {
    "c": "LEFT JOIN customers c ON c.id = o.customer_id",
    "e": "LEFT JOIN employees e ON e.id = o.employee_id",
    "oi": "LEFT JOIN order_items oi ON oi.order_id = o.id",
    "p": "LEFT JOIN products p ON p.id = oi.product_id",
}


_METRICS: list[MetricDef] = [
    MetricDef(
        name="orders_count",
        label="Orders",
        description="Total orders in the filter window.",
        expr="COUNT(DISTINCT o.id)::int",
        format="integer",
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'How many orders did we get last 30 days?' "
            "-> compile_metric(metric='sales.orders_count', filters={'period':'last_30d'})"
        ),
    ),
    MetricDef(
        name="revenue_total",
        label="Revenue",
        description="Sum of order.total for orders NOT in ('cancelled','refunded').",
        expr="COALESCE(SUM(o.total) FILTER (WHERE o.status NOT IN ('cancelled','refunded')), 0)::numeric",
        format="currency_usd",
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'Revenue by product category this quarter' "
            "-> compile_metric(metric='sales.revenue_total', dimensions=['product_category'], "
            "filters={'period':'qtd'})"
        ),
    ),
    MetricDef(
        name="aov",
        label="Average Order Value",
        description="Mean order.total across non-cancelled/non-refunded orders.",
        expr=(
            "COALESCE(AVG(o.total) FILTER "
            "(WHERE o.status NOT IN ('cancelled','refunded')), 0)::numeric"
        ),
        format="currency_usd",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'What is our AOV in Q1 2026?' "
            "-> compile_metric(metric='sales.aov', filters={'period':'q1_2026'})"
        ),
    ),
    MetricDef(
        name="units_sold",
        label="Units Sold",
        description="Sum of order_items.quantity for non-cancelled orders. Requires oi.",
        expr=(
            "COALESCE(SUM(oi.quantity) FILTER "
            "(WHERE o.status NOT IN ('cancelled','refunded')), 0)::int"
        ),
        format="integer",
        required_joins=("oi",),
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'Units sold per product category last month' "
            "-> compile_metric(metric='sales.units_sold', dimensions=['product_category'], "
            "filters={'period':'last_30d'})"
        ),
    ),
    MetricDef(
        name="unique_customers",
        label="Unique Customers",
        description="Distinct customers who placed at least one order in the window.",
        expr="COUNT(DISTINCT o.customer_id)::int",
        format="integer",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'How many customers ordered last quarter?' "
            "-> compile_metric(metric='sales.unique_customers', filters={'period':'qtd'})"
        ),
    ),
    MetricDef(
        name="cancelled_rate_pct",
        label="Cancellation Rate",
        description="100 * cancelled orders / all orders in the window.",
        expr=(
            "ROUND(100.0 * NULLIF("
            "COUNT(*) FILTER (WHERE o.status = 'cancelled'), 0)::numeric "
            "/ NULLIF(COUNT(*), 0), 2)"
        ),
        format="percentage",
        chart_hint=ChartHint(type="line", x_key="dim_1"),
        example_use=(
            "User: 'Cancellation rate by month' "
            "-> compile_metric(metric='sales.cancelled_rate_pct', dimensions=['order_month'])"
        ),
    ),
    MetricDef(
        name="refund_rate_pct",
        label="Refund Rate",
        description="100 * refunded orders / all orders in the window.",
        expr=(
            "ROUND(100.0 * NULLIF("
            "COUNT(*) FILTER (WHERE o.status = 'refunded'), 0)::numeric "
            "/ NULLIF(COUNT(*), 0), 2)"
        ),
        format="percentage",
        chart_hint=ChartHint(type="line", x_key="dim_1"),
        example_use=(
            "User: 'Refund rate by segment' "
            "-> compile_metric(metric='sales.refund_rate_pct', dimensions=['customer_segment'])"
        ),
    ),
]


_DIMS: list[DimensionDef] = [
    DimensionDef(
        name="status",
        label="Order Status",
        description="Order status (pending/paid/shipped/delivered/cancelled/refunded).",
        expr="o.status",
    ),
    DimensionDef(
        name="customer_country",
        label="Customer Country",
        description="Country of the customer who placed the order.",
        expr="c.country",
        required_joins=("c",),
    ),
    DimensionDef(
        name="customer_segment",
        label="Customer Segment",
        description="Customer segment (consumer/sme/enterprise).",
        expr="c.segment",
        required_joins=("c",),
    ),
    DimensionDef(
        name="product_category",
        label="Product Category",
        description=(
            "Product category. Note: joins via order_items, so revenue attributed "
            "here is the sum of items belonging to that category."
        ),
        expr="p.category",
        required_joins=("oi", "p"),
    ),
    DimensionDef(
        name="employee",
        label="Sales Employee",
        description="Employee (order owner) full name.",
        expr="COALESCE(e.first_name || ' ' || e.last_name, '(unassigned)')",
        required_joins=("e",),
    ),
    DimensionDef(
        name="order_day",
        label="Day",
        description="Order date, formatted YYYY-MM-DD.",
        expr="to_char(date_trunc('day', o.created_at), 'YYYY-MM-DD')",
        time_grain="day",
    ),
    DimensionDef(
        name="order_month",
        label="Month",
        description="Calendar month of the order, formatted YYYY-MM.",
        expr="to_char(date_trunc('month', o.created_at), 'YYYY-MM')",
        time_grain="month",
    ),
    DimensionDef(
        name="order_quarter",
        label="Quarter",
        description="Calendar quarter, formatted YYYY-Qn.",
        expr="""to_char(date_trunc('quarter', o.created_at), 'YYYY-"Q"Q')""",
        time_grain="quarter",
    ),
]


DOMAIN = DomainDef(
    name="sales",
    fact_table="orders",
    fact_alias="o",
    description="Orders fact + joined customer, employee, order_items, product dims.",
    joins=_JOINS,
    metrics=_METRICS,
    dimensions=_DIMS,
    supported_filters=(
        "period",
        "from_date",
        "to_date",
        "country",
        "segment",
        "category",
        "status",
        "employee_id",
    ),
    time_column="o.created_at",
)
