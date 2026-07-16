"""Inventory domain — inventory rows (product x warehouse) as fact.

Joins:
  p -> products    (i.product_id   = p.id)
  w -> warehouses  (i.warehouse_id = w.id)

Inventory has no time dimension in the operational schema (updated_at only).
Period filters are ignored.
"""

from __future__ import annotations

from multirag.semantic.registry.base import (
    ChartHint,
    DimensionDef,
    DomainDef,
    MetricDef,
)

_JOINS = {
    "p": "LEFT JOIN products p ON p.id = i.product_id",
    "w": "LEFT JOIN warehouses w ON w.id = i.warehouse_id",
}

_METRICS: list[MetricDef] = [
    MetricDef(
        name="stock_on_hand",
        label="Stock On Hand",
        description="Sum of quantity_on_hand across inventory rows in the filter window.",
        expr="COALESCE(SUM(i.quantity_on_hand), 0)::int",
        format="integer",
        chart_hint=ChartHint(type="bar", x_key="dim_1"),
        example_use=(
            "User: 'Stock on hand by warehouse' "
            "-> compile_metric(metric='inventory.stock_on_hand', dimensions=['warehouse'])"
        ),
    ),
    MetricDef(
        name="skus_in_stock",
        label="SKUs In Stock",
        description="Distinct products with quantity_on_hand > 0.",
        expr="COUNT(DISTINCT i.product_id) FILTER (WHERE i.quantity_on_hand > 0)::int",
        format="integer",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'How many SKUs are currently stocked?' "
            "-> compile_metric(metric='inventory.skus_in_stock')"
        ),
    ),
    MetricDef(
        name="low_stock_products",
        label="Low-Stock Products",
        description=(
            "Distinct products whose quantity_on_hand is at or below their "
            "reorder_level — i.e. items that need re-ordering."
        ),
        expr="COUNT(DISTINCT i.product_id) FILTER (WHERE i.quantity_on_hand <= i.reorder_level)::int",
        format="integer",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'Which categories have the most low-stock items?' "
            "-> compile_metric(metric='inventory.low_stock_products', dimensions=['product_category'])"
        ),
    ),
    MetricDef(
        name="out_of_stock_products",
        label="Out-of-Stock Products",
        description="Distinct products with zero quantity_on_hand.",
        expr="COUNT(DISTINCT i.product_id) FILTER (WHERE i.quantity_on_hand = 0)::int",
        format="integer",
        chart_hint=ChartHint(type="kpi"),
        example_use=(
            "User: 'How many products are out of stock right now?' "
            "-> compile_metric(metric='inventory.out_of_stock_products')"
        ),
    ),
]


_DIMS: list[DimensionDef] = [
    DimensionDef(
        name="product_category",
        label="Product Category",
        description="Category of the product.",
        expr="p.category",
        required_joins=("p",),
    ),
    DimensionDef(
        name="product",
        label="Product",
        description="Product name.",
        expr="p.name",
        required_joins=("p",),
    ),
    DimensionDef(
        name="warehouse",
        label="Warehouse",
        description="Warehouse name.",
        expr="w.name",
        required_joins=("w",),
    ),
    DimensionDef(
        name="warehouse_country",
        label="Warehouse Country",
        description="Country the warehouse is located in.",
        expr="w.country",
        required_joins=("w",),
    ),
]


DOMAIN = DomainDef(
    name="inventory",
    fact_table="inventory",
    fact_alias="i",
    description="Inventory fact (product x warehouse) with product + warehouse dims.",
    joins=_JOINS,
    metrics=_METRICS,
    dimensions=_DIMS,
    supported_filters=("category", "warehouse_id"),
    time_column=None,
)
