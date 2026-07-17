"""Finance domain — transactions as fact.

Joins:
  o -> orders (t.order_id = o.id) — for cross-refs to order status if needed
"""

from __future__ import annotations

from multirag.semantic.registry.base import (
    ChartHint,
    DimensionDef,
    DomainDef,
    MetricDef,
)

_JOINS = {
    "o": "LEFT JOIN orders o ON o.id = t.order_id",
}


_METRICS: list[MetricDef] = [
    MetricDef(
        name="transactions_total",
        label="Transactions",
        description="Total transaction rows in the filter window.",
        expr="COUNT(*)::int",
        format="integer",
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'How many transactions last 7 days?' "
            "-> compile_metric(metric='finance.transactions_total', filters={'period':'last_7d'})"
        ),
    ),
    MetricDef(
        name="gross_processed",
        label="Gross Processed",
        description="Sum of amount for succeeded transactions.",
        expr="COALESCE(SUM(t.amount) FILTER (WHERE t.status = 'succeeded'), 0)::numeric",
        format="currency_usd",
        chart_hint=ChartHint(type="line", x_key="dim_1"),
        example_use=(
            "User: 'Gross processed by payment method this month' "
            "-> compile_metric(metric='finance.gross_processed', dimensions=['method'], "
            "filters={'period':'mtd'})"
        ),
    ),
    MetricDef(
        name="refunded_amount",
        label="Refunded Amount",
        description="Sum of amount for refunded transactions.",
        expr="COALESCE(SUM(t.amount) FILTER (WHERE t.status = 'refunded'), 0)::numeric",
        format="currency_usd",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'Total refunded amount YTD' "
            "-> compile_metric(metric='finance.refunded_amount', filters={'period':'ytd'})"
        ),
    ),
    MetricDef(
        name="failure_rate_pct",
        label="Failure Rate",
        description="100 * failed transactions / all transactions.",
        expr=(
            "ROUND(100.0 * NULLIF("
            "COUNT(*) FILTER (WHERE t.status = 'failed'), 0)::numeric "
            "/ NULLIF(COUNT(*), 0), 2)"
        ),
        format="percentage",
        chart_hint=ChartHint(type="line", x_key="dim_1"),
        example_use=(
            "User: 'Payment failure rate by method' "
            "-> compile_metric(metric='finance.failure_rate_pct', dimensions=['method'])"
        ),
    ),
    MetricDef(
        name="chargeback_rate_pct",
        label="Chargeback Rate",
        description="100 * chargeback transactions / all transactions.",
        expr=(
            "ROUND(100.0 * NULLIF("
            "COUNT(*) FILTER (WHERE t.status = 'chargeback'), 0)::numeric "
            "/ NULLIF(COUNT(*), 0), 2)"
        ),
        format="percentage",
        chart_hint=ChartHint(type="line", x_key="dim_1"),
        example_use=(
            "User: 'Chargeback rate trend by month' "
            "-> compile_metric(metric='finance.chargeback_rate_pct', dimensions=['txn_month'])"
        ),
    ),
]


_DIMS: list[DimensionDef] = [
    DimensionDef(
        name="method",
        label="Payment Method",
        description="Payment method (card/wallet/bank_transfer/cod).",
        expr="t.method",
    ),
    DimensionDef(
        name="status",
        label="Transaction Status",
        description="succeeded / failed / refunded / chargeback.",
        expr="t.status",
    ),
    DimensionDef(
        name="txn_day",
        label="Day",
        description="Transaction date, formatted YYYY-MM-DD.",
        expr="to_char(date_trunc('day', t.processed_at), 'YYYY-MM-DD')",
        time_grain="day",
    ),
    DimensionDef(
        name="txn_month",
        label="Month",
        description="Calendar month of the transaction, formatted YYYY-MM.",
        expr="to_char(date_trunc('month', t.processed_at), 'YYYY-MM')",
        time_grain="month",
    ),
    DimensionDef(
        name="txn_quarter",
        label="Quarter",
        description="Calendar quarter, YYYY-Qn.",
        expr="""to_char(date_trunc('quarter', t.processed_at), 'YYYY-"Q"Q')""",
        time_grain="quarter",
    ),
]


DOMAIN = DomainDef(
    name="finance",
    fact_table="transactions",
    fact_alias="t",
    description="Transactions fact — payment throughput, failures, refunds.",
    joins=_JOINS,
    metrics=_METRICS,
    dimensions=_DIMS,
    supported_filters=("period", "from_date", "to_date", "status"),
    time_column="t.processed_at",
)
