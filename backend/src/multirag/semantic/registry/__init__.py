"""Domain registries + merged lookup surface for the LLM tools.

Every domain module (sales, inventory, hr, finance) exposes a `DOMAIN: DomainDef`.
This module merges them, validates once at import time, and exposes:

  - `DOMAINS`                    — dict[str, DomainDef]
  - `find_metric(namespaced_name)` -> tuple[DomainDef, MetricDef] | None
  - `find_dimension(domain, name)` -> DimensionDef | None
  - `metric_names()`             -> list[str] of "<domain>.<name>"
  - `compact_catalog()`          -> plain-text catalog for the system prompt
  - `list_metrics_catalog()`     -> structured JSON for the `list_metrics` tool
"""

from __future__ import annotations

from multirag.logging import get_logger
from multirag.semantic.registry.base import DimensionDef, DomainDef, MetricDef
from multirag.semantic.registry.finance import DOMAIN as FINANCE_DOMAIN
from multirag.semantic.registry.hr import DOMAIN as HR_DOMAIN
from multirag.semantic.registry.inventory import DOMAIN as INVENTORY_DOMAIN
from multirag.semantic.registry.sales import DOMAIN as SALES_DOMAIN

log = get_logger(__name__)

DOMAINS: dict[str, DomainDef] = {
    d.name: d
    for d in (SALES_DOMAIN, INVENTORY_DOMAIN, HR_DOMAIN, FINANCE_DOMAIN)
}


def _validate_all() -> None:
    errors: list[str] = []
    seen_domains: set[str] = set()

    for name, d in DOMAINS.items():
        if name in seen_domains:
            errors.append(f"duplicate domain '{name}'")
        seen_domains.add(name)

        seen_metrics: set[str] = set()
        for m in d.metrics:
            if not m.name or not m.name.replace("_", "").isalnum():
                errors.append(f"[{name}] metric '{m.name}': must be snake_case alphanumeric")
            if m.name in seen_metrics:
                errors.append(f"[{name}] duplicate metric name '{m.name}'")
            seen_metrics.add(m.name)
            if not m.description.strip():
                errors.append(f"[{name}.{m.name}] description is empty")
            if not m.expr.strip():
                errors.append(f"[{name}.{m.name}] expr is empty")
            if not m.example_use.strip():
                errors.append(f"[{name}.{m.name}] example_use is empty")

        seen_dims: set[str] = set()
        declared_joins = set(d.joins.keys())
        for dim in d.dimensions:
            if dim.name in seen_dims:
                errors.append(f"[{name}] duplicate dimension '{dim.name}'")
            seen_dims.add(dim.name)
            if not dim.expr.strip():
                errors.append(f"[{name}.{dim.name}] expr is empty")
            for required in dim.required_joins:
                if required not in declared_joins:
                    errors.append(
                        f"[{name}.{dim.name}] requires join alias '{required}' "
                        f"but domain only declares joins {sorted(declared_joins)}"
                    )

    if errors:
        for e in errors:
            log.error("registry.validation.fail", detail=e)
        raise ValueError(
            f"Semantic registry has {len(errors)} validation error(s). First: {errors[0]}"
        )

    total_metrics = sum(len(d.metrics) for d in DOMAINS.values())
    total_dims = sum(len(d.dimensions) for d in DOMAINS.values())
    log.info(
        "registry.validated",
        domains=len(DOMAINS),
        metrics=total_metrics,
        dimensions=total_dims,
    )


_validate_all()


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

def _split_namespaced(name: str) -> tuple[str, str]:
    if "." not in name:
        raise ValueError(
            f"metric name '{name}' must be namespaced as '<domain>.<metric>' "
            f"(e.g. 'sales.revenue_total'). Known domains: {sorted(DOMAINS)}"
        )
    domain, metric = name.split(".", 1)
    return domain, metric


def find_metric(namespaced_name: str) -> tuple[DomainDef, MetricDef] | None:
    try:
        domain_name, metric_name = _split_namespaced(namespaced_name)
    except ValueError:
        return None
    domain = DOMAINS.get(domain_name)
    if not domain:
        return None
    for m in domain.metrics:
        if m.name == metric_name:
            return domain, m
    return None


def find_dimension(domain_name: str, dim_name: str) -> DimensionDef | None:
    domain = DOMAINS.get(domain_name)
    if not domain:
        return None
    return next((d for d in domain.dimensions if d.name == dim_name), None)


def metric_names() -> list[str]:
    return [f"{d.name}.{m.name}" for d in DOMAINS.values() for m in d.metrics]


def dimension_names(domain_name: str) -> list[str]:
    domain = DOMAINS.get(domain_name)
    return [d.name for d in domain.dimensions] if domain else []


def compact_catalog() -> str:
    """Plain-text catalog embedded in the system prompt at boot."""
    lines: list[str] = []
    for d in DOMAINS.values():
        lines.append(f"DOMAIN: {d.name} — fact table `{d.fact_table}`")
        lines.append("  METRICS:")
        for m in d.metrics:
            lines.append(f"    {d.name}.{m.name} — {m.description} [{m.format}]")
        lines.append("  DIMENSIONS:")
        for dim in d.dimensions:
            grain = f" (time grain: {dim.time_grain})" if dim.time_grain else ""
            lines.append(f"    {dim.name} — {dim.description}{grain}")
        lines.append("")
    return "\n".join(lines).rstrip()


def list_metrics_catalog() -> list[dict]:
    """Structured metric catalog for the `list_metrics` tool. No SQL exposed."""
    return [
        {
            "name": f"{d.name}.{m.name}",
            "domain": d.name,
            "label": m.label,
            "description": m.description,
            "format": m.format,
            "chart_hint": {"type": m.chart_hint.type, "x_key": m.chart_hint.x_key},
            "example_use": m.example_use,
        }
        for d in DOMAINS.values()
        for m in d.metrics
    ]
