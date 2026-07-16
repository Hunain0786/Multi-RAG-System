"""HR domain — employees as fact table.

No joins in v1. Period filters map onto `hired_at` so 'headcount hired last 90d'
etc. works out of the box.
"""

from __future__ import annotations

from multirag.semantic.registry.base import (
    ChartHint,
    DimensionDef,
    DomainDef,
    MetricDef,
)

_METRICS: list[MetricDef] = [
    MetricDef(
        name="headcount",
        label="Headcount",
        description="Total employees whose hired_at falls within the filter window.",
        expr="COUNT(*)::int",
        format="integer",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'How many employees do we have?' "
            "-> compile_metric(metric='hr.headcount')"
        ),
    ),
    MetricDef(
        name="new_hires",
        label="New Hires",
        description="Employees hired in the filter window (same as headcount when period is set).",
        expr="COUNT(*)::int",
        format="integer",
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'New hires by department in Q1 2026' "
            "-> compile_metric(metric='hr.new_hires', dimensions=['department'], "
            "filters={'period':'q1_2026'})"
        ),
    ),
    MetricDef(
        name="avg_tenure_days",
        label="Avg Tenure (days)",
        description="Mean days between hired_at and today across employees.",
        expr="ROUND(AVG(EXTRACT(EPOCH FROM (NOW() - e.hired_at)) / 86400)::numeric, 1)",
        format="days",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'Average tenure by department' "
            "-> compile_metric(metric='hr.avg_tenure_days', dimensions=['department'])"
        ),
    ),
    MetricDef(
        name="avg_salary",
        label="Avg Salary",
        description="Mean salary in the filter window (USD-denominated).",
        expr="ROUND(AVG(e.salary)::numeric, 2)",
        format="currency_usd",
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'Average salary by department' "
            "-> compile_metric(metric='hr.avg_salary', dimensions=['department'])"
        ),
    ),
    MetricDef(
        name="salary_total",
        label="Total Payroll",
        description="Sum of employee salary in the filter window.",
        expr="COALESCE(SUM(e.salary), 0)::numeric",
        format="currency_usd",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'Total payroll cost' "
            "-> compile_metric(metric='hr.salary_total')"
        ),
    ),
]


_DIMS: list[DimensionDef] = [
    DimensionDef(
        name="department",
        label="Department",
        description="Department (sales/support/engineering/ops/finance).",
        expr="e.department",
    ),
    DimensionDef(
        name="role",
        label="Role",
        description="Role/title within a department.",
        expr="e.role",
    ),
    DimensionDef(
        name="hire_month",
        label="Hire Month",
        description="Month the employee was hired, formatted YYYY-MM.",
        expr="to_char(date_trunc('month', e.hired_at), 'YYYY-MM')",
        time_grain="month",
    ),
    DimensionDef(
        name="hire_year",
        label="Hire Year",
        description="Calendar year the employee was hired.",
        expr="EXTRACT(year FROM e.hired_at)::int",
        time_grain="year",
    ),
]


DOMAIN = DomainDef(
    name="hr",
    fact_table="employees",
    fact_alias="e",
    description="Employees fact — headcount, tenure, salary.",
    metrics=_METRICS,
    dimensions=_DIMS,
    supported_filters=("period", "from_date", "to_date"),
    time_column="e.hired_at",
)
