"""Insight engine.

Each check is a coroutine that computes a headline number for a `current`
period and (where applicable) the equivalent `prior` window, then produces one
or more `Insight` records.

Design notes:
  - Windows use explicit `from`/`to` dates so the "prior period" is truly the
    same-length window immediately preceding the current one — no ambiguity.
  - Every check catches its own errors and returns a `severity="unknown"`
    entry rather than raising, so a single broken metric can never fail the
    whole endpoint.
  - Result shape is intentionally close to what the agent's analyst playbook
    describes (number + trend + so-what), so the frontend can render both this
    endpoint and the chat's risk block with the same card.
"""

from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any, Literal

from multirag.db.pool import fetch_conn
from multirag.logging import get_logger
from multirag.semantic.compile import (
    CompiledComposite,
    CompiledQuery,
    compile_composite,
    compile_metric,
    run_compiled,
)

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Cold-start guard
# ---------------------------------------------------------------------------
#
# When the Postgres backend is a serverless offering (e.g. Neon), the compute
# suspends after ~5 min of idle. The very first request after that has to
# wake the compute, which typically takes 3-10s. If /insights fires 4
# parallel checks straight into a cold pool, they all race to reconnect,
# and psycopg_pool's default 30s acquisition timeout can expire on ALL of
# them at once (see PoolTimeout in local dev logs).
#
# Fix: pay the cold-start cost ONCE, on a single connection, before the
# parallel fan-out. If this succeeds every subsequent check is essentially
# free because the pool already holds an open, warm connection.


async def _prewarm(timeout_s: float = 45.0) -> bool:
    """Fire a trivial query so the pool opens (and Neon wakes) before fan-out."""
    try:
        async with asyncio.timeout(timeout_s):
            async with fetch_conn() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1;")
                    await cur.fetchone()
        return True
    except Exception as e:  # noqa: BLE001
        log.warning("insights.prewarm.failed", error=str(e))
        return False


Severity = Literal["good", "info", "low", "med", "high", "unknown"]


@dataclass
class Insight:
    id: str
    severity: Severity
    category: str  # 'sales' | 'inventory' | 'finance' | 'hr' | 'ops'
    title: str
    detail: str
    metric: str | None = None
    value: float | int | None = None
    prior_value: float | int | None = None
    delta_pct: float | None = None
    unit: str | None = None  # 'currency_usd' | 'percentage' | 'integer' | ...
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# ---------------------------------------------------------------------------
# Period helpers
# ---------------------------------------------------------------------------


def _last_n_days_window(n: int, ref: date | None = None) -> tuple[date, date, date, date]:
    """Return `(cur_from, cur_to, prior_from, prior_to)` for a rolling n-day window."""
    today = ref or datetime.now(timezone.utc).date()
    cur_to = today
    cur_from = today - timedelta(days=n)
    prior_to = cur_from - timedelta(days=1)
    prior_from = prior_to - timedelta(days=n)
    return cur_from, cur_to, prior_from, prior_to


def _pct_change(current: float | None, prior: float | None) -> float | None:
    if current is None or prior is None:
        return None
    if prior == 0:
        return None if current == 0 else 100.0
    return round(((current - prior) / prior) * 100.0, 1)


# ---------------------------------------------------------------------------
# Single-scalar helpers
# ---------------------------------------------------------------------------


async def _scalar_metric(metric: str, filters: dict[str, Any]) -> float | None:
    """Compile + run a single metric with no dimensions; return the scalar `value`."""
    q: CompiledQuery = compile_metric(metric_name=metric, filters=filters, limit=1)
    rows = await run_compiled(q)
    if not rows:
        return None
    v = rows[0].get("value")
    if v is None:
        return None
    return float(v) if isinstance(v, (int, float)) else v


async def _composite_row(
    metrics: list[dict[str, str]], filters: dict[str, Any]
) -> dict[str, Any]:
    q: CompiledComposite = compile_composite(metrics=metrics, filters=filters)
    rows = await run_compiled(q)
    return rows[0] if rows else {}


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


async def _check_sales_kpis_30d() -> list[Insight]:
    """Revenue, AOV, orders, refund_rate over last 30d vs prior 30d."""
    cur_from, cur_to, prior_from, prior_to = _last_n_days_window(30)
    metrics = [
        {"alias": "revenue", "metric": "sales.revenue_total"},
        {"alias": "aov", "metric": "sales.aov"},
        {"alias": "orders", "metric": "sales.orders_count"},
        {"alias": "refund_rate", "metric": "sales.refund_rate_pct"},
        {"alias": "cancelled_rate", "metric": "sales.cancelled_rate_pct"},
    ]

    try:
        cur = await _composite_row(
            metrics, {"from": cur_from.isoformat(), "to": cur_to.isoformat()}
        )
        prior = await _composite_row(
            metrics, {"from": prior_from.isoformat(), "to": prior_to.isoformat()}
        )
    except Exception as e:  # noqa: BLE001
        log.warning("insights.sales_kpis.failed", error=str(e))
        return [
            Insight(
                id="sales.kpis.error",
                severity="unknown",
                category="sales",
                title="Sales KPIs unavailable",
                detail=f"Could not compute the last-30d KPI snapshot: {e}",
            )
        ]

    out: list[Insight] = []

    def _f(v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    # Revenue trend
    rev_cur = _f(cur.get("revenue")) or 0.0
    rev_prior = _f(prior.get("revenue")) or 0.0
    rev_delta = _pct_change(rev_cur, rev_prior)
    rev_sev: Severity = "info"
    detail_bits = [f"${rev_cur:,.0f} in the last 30d vs ${rev_prior:,.0f} in the prior 30d."]
    if rev_delta is not None:
        detail_bits.append(f"{rev_delta:+.1f}% vs prior 30d.")
        if rev_delta <= -10:
            rev_sev = "high"
        elif rev_delta <= -5:
            rev_sev = "med"
        elif rev_delta >= 10:
            rev_sev = "good"
    out.append(
        Insight(
            id="sales.revenue.30d",
            severity=rev_sev,
            category="sales",
            title="Revenue (last 30d)",
            detail=" ".join(detail_bits),
            metric="sales.revenue_total",
            value=rev_cur,
            prior_value=rev_prior,
            delta_pct=rev_delta,
            unit="currency_usd",
        )
    )

    # AOV trend
    aov_cur = _f(cur.get("aov")) or 0.0
    aov_prior = _f(prior.get("aov")) or 0.0
    aov_delta = _pct_change(aov_cur, aov_prior)
    aov_sev: Severity = "info"
    aov_bits = [f"${aov_cur:,.2f} last 30d vs ${aov_prior:,.2f} prior 30d."]
    if aov_delta is not None:
        aov_bits.append(f"{aov_delta:+.1f}% vs prior 30d.")
        if aov_delta <= -15:
            aov_sev = "high"
        elif aov_delta <= -5:
            aov_sev = "med"
    out.append(
        Insight(
            id="sales.aov.30d",
            severity=aov_sev,
            category="sales",
            title="Average order value (last 30d)",
            detail=" ".join(aov_bits),
            metric="sales.aov",
            value=aov_cur,
            prior_value=aov_prior,
            delta_pct=aov_delta,
            unit="currency_usd",
        )
    )

    # Orders trend
    ord_cur = _f(cur.get("orders")) or 0.0
    ord_prior = _f(prior.get("orders")) or 0.0
    ord_delta = _pct_change(ord_cur, ord_prior)
    ord_sev: Severity = "info"
    ord_bits = [f"{int(ord_cur):,} orders last 30d vs {int(ord_prior):,} prior 30d."]
    if ord_delta is not None:
        ord_bits.append(f"{ord_delta:+.1f}% vs prior 30d.")
        if ord_delta <= -10:
            ord_sev = "high"
        elif ord_delta <= -5:
            ord_sev = "med"
    out.append(
        Insight(
            id="sales.orders.30d",
            severity=ord_sev,
            category="sales",
            title="Order volume (last 30d)",
            detail=" ".join(ord_bits),
            metric="sales.orders_count",
            value=ord_cur,
            prior_value=ord_prior,
            delta_pct=ord_delta,
            unit="integer",
        )
    )

    # Refund rate (absolute + spike)
    refund_cur = _f(cur.get("refund_rate")) or 0.0
    refund_prior = _f(prior.get("refund_rate")) or 0.0
    refund_delta_pp = round(refund_cur - refund_prior, 2)
    refund_sev: Severity = "info"
    if refund_cur >= 8.0 or refund_delta_pp >= 3.0:
        refund_sev = "high"
    elif refund_cur >= 5.0 or refund_delta_pp >= 1.5:
        refund_sev = "med"
    out.append(
        Insight(
            id="sales.refund_rate.30d",
            severity=refund_sev,
            category="sales",
            title="Refund rate (last 30d)",
            detail=(
                f"{refund_cur:.2f}% last 30d vs {refund_prior:.2f}% prior "
                f"({refund_delta_pp:+.2f}pp)."
            ),
            metric="sales.refund_rate_pct",
            value=refund_cur,
            prior_value=refund_prior,
            delta_pct=_pct_change(refund_cur, refund_prior),
            unit="percentage",
        )
    )

    # Cancellation rate
    cancel_cur = _f(cur.get("cancelled_rate")) or 0.0
    cancel_prior = _f(prior.get("cancelled_rate")) or 0.0
    cancel_delta_pp = round(cancel_cur - cancel_prior, 2)
    cancel_sev: Severity = "info"
    if cancel_cur >= 8.0 or cancel_delta_pp >= 3.0:
        cancel_sev = "high"
    elif cancel_cur >= 5.0:
        cancel_sev = "med"
    out.append(
        Insight(
            id="sales.cancelled_rate.30d",
            severity=cancel_sev,
            category="sales",
            title="Cancellation rate (last 30d)",
            detail=(
                f"{cancel_cur:.2f}% last 30d vs {cancel_prior:.2f}% prior "
                f"({cancel_delta_pp:+.2f}pp)."
            ),
            metric="sales.cancelled_rate_pct",
            value=cancel_cur,
            prior_value=cancel_prior,
            delta_pct=_pct_change(cancel_cur, cancel_prior),
            unit="percentage",
        )
    )

    return out


async def _check_finance_health_30d() -> list[Insight]:
    """Payment failure + chargeback rate over the last 30d vs prior 30d."""
    cur_from, cur_to, prior_from, prior_to = _last_n_days_window(30)
    metrics = [
        {"alias": "failure", "metric": "finance.failure_rate_pct"},
        {"alias": "chargeback", "metric": "finance.chargeback_rate_pct"},
        {"alias": "gross", "metric": "finance.gross_processed"},
    ]
    try:
        cur = await _composite_row(
            metrics, {"from": cur_from.isoformat(), "to": cur_to.isoformat()}
        )
        prior = await _composite_row(
            metrics, {"from": prior_from.isoformat(), "to": prior_to.isoformat()}
        )
    except Exception as e:  # noqa: BLE001
        log.warning("insights.finance_health.failed", error=str(e))
        return [
            Insight(
                id="finance.health.error",
                severity="unknown",
                category="finance",
                title="Payment health unavailable",
                detail=f"Could not compute payment health: {e}",
            )
        ]

    def _f(v: Any) -> float | None:
        if v is None:
            return None
        try:
            return float(v)
        except (TypeError, ValueError):
            return None

    out: list[Insight] = []

    fail_cur = _f(cur.get("failure")) or 0.0
    fail_prior = _f(prior.get("failure")) or 0.0
    fail_sev: Severity = "info"
    if fail_cur >= 5.0:
        fail_sev = "high"
    elif fail_cur >= 2.0:
        fail_sev = "med"
    out.append(
        Insight(
            id="finance.failure_rate.30d",
            severity=fail_sev,
            category="finance",
            title="Payment failure rate (last 30d)",
            detail=(
                f"{fail_cur:.2f}% last 30d vs {fail_prior:.2f}% prior 30d."
            ),
            metric="finance.failure_rate_pct",
            value=fail_cur,
            prior_value=fail_prior,
            delta_pct=_pct_change(fail_cur, fail_prior),
            unit="percentage",
        )
    )

    cb_cur = _f(cur.get("chargeback")) or 0.0
    cb_prior = _f(prior.get("chargeback")) or 0.0
    cb_sev: Severity = "info"
    if cb_cur >= 1.0:
        cb_sev = "high"
    elif cb_cur >= 0.5:
        cb_sev = "med"
    out.append(
        Insight(
            id="finance.chargeback_rate.30d",
            severity=cb_sev,
            category="finance",
            title="Chargeback rate (last 30d)",
            detail=(
                f"{cb_cur:.2f}% last 30d vs {cb_prior:.2f}% prior 30d."
            ),
            metric="finance.chargeback_rate_pct",
            value=cb_cur,
            prior_value=cb_prior,
            delta_pct=_pct_change(cb_cur, cb_prior),
            unit="percentage",
        )
    )

    gross_cur = _f(cur.get("gross")) or 0.0
    gross_prior = _f(prior.get("gross")) or 0.0
    gross_delta = _pct_change(gross_cur, gross_prior)
    gross_sev: Severity = "info"
    if gross_delta is not None:
        if gross_delta <= -10:
            gross_sev = "high"
        elif gross_delta <= -5:
            gross_sev = "med"
        elif gross_delta >= 10:
            gross_sev = "good"
    out.append(
        Insight(
            id="finance.gross_processed.30d",
            severity=gross_sev,
            category="finance",
            title="Gross processed (last 30d)",
            detail=(
                f"${gross_cur:,.0f} last 30d vs ${gross_prior:,.0f} prior 30d"
                + (f" ({gross_delta:+.1f}%)." if gross_delta is not None else ".")
            ),
            metric="finance.gross_processed",
            value=gross_cur,
            prior_value=gross_prior,
            delta_pct=gross_delta,
            unit="currency_usd",
        )
    )

    return out


async def _check_inventory_now() -> list[Insight]:
    """Low-stock / out-of-stock right now (inventory has no time filter)."""
    try:
        low = await _scalar_metric("inventory.low_stock_products", {})
        out_ = await _scalar_metric("inventory.out_of_stock_products", {})
    except Exception as e:  # noqa: BLE001
        log.warning("insights.inventory.failed", error=str(e))
        return [
            Insight(
                id="inventory.error",
                severity="unknown",
                category="inventory",
                title="Inventory check unavailable",
                detail=f"Could not compute inventory status: {e}",
            )
        ]

    insights: list[Insight] = []

    low_n = int(low or 0)
    low_sev: Severity = "good"
    if low_n >= 10:
        low_sev = "high"
    elif low_n >= 3:
        low_sev = "med"
    elif low_n > 0:
        low_sev = "low"
    insights.append(
        Insight(
            id="inventory.low_stock.now",
            severity=low_sev,
            category="inventory",
            title="Low-stock SKUs",
            detail=(
                f"{low_n} SKU(s) are at or below their reorder level right now."
                if low_n
                else "No SKUs are below their reorder level."
            ),
            metric="inventory.low_stock_products",
            value=low_n,
            unit="integer",
        )
    )

    oos_n = int(out_ or 0)
    oos_sev: Severity = "good"
    if oos_n >= 5:
        oos_sev = "high"
    elif oos_n > 0:
        oos_sev = "med"
    insights.append(
        Insight(
            id="inventory.out_of_stock.now",
            severity=oos_sev,
            category="inventory",
            title="Out-of-stock SKUs",
            detail=(
                f"{oos_n} SKU(s) are currently out of stock across all warehouses."
                if oos_n
                else "No SKUs are out of stock."
            ),
            metric="inventory.out_of_stock_products",
            value=oos_n,
            unit="integer",
        )
    )

    return insights


async def _check_top_category_mover_30d() -> list[Insight]:
    """Which product category moved the most (up or down) in revenue vs prior 30d."""
    cur_from, cur_to, prior_from, prior_to = _last_n_days_window(30)
    try:
        q_cur = compile_metric(
            metric_name="sales.revenue_total",
            dimensions=["product_category"],
            filters={"from": cur_from.isoformat(), "to": cur_to.isoformat()},
            limit=50,
        )
        q_prior = compile_metric(
            metric_name="sales.revenue_total",
            dimensions=["product_category"],
            filters={"from": prior_from.isoformat(), "to": prior_to.isoformat()},
            limit=50,
        )
        rows_cur = await run_compiled(q_cur)
        rows_prior = await run_compiled(q_prior)
    except Exception as e:  # noqa: BLE001
        log.warning("insights.top_category.failed", error=str(e))
        return []

    prior_map = {r.get("dim_1"): float(r.get("value") or 0.0) for r in rows_prior}
    diffs: list[tuple[str, float, float, float]] = []  # (cat, cur, prior, delta_pct)
    for r in rows_cur:
        cat = r.get("dim_1")
        cur_v = float(r.get("value") or 0.0)
        prior_v = prior_map.get(cat, 0.0)
        delta = _pct_change(cur_v, prior_v)
        if delta is None:
            continue
        diffs.append((str(cat or "(none)"), cur_v, prior_v, delta))

    if not diffs:
        return []

    diffs.sort(key=lambda t: abs(t[3]), reverse=True)
    top_cat, cur_v, prior_v, delta = diffs[0]

    sev: Severity = "info"
    if delta <= -20:
        sev = "high"
    elif delta <= -10:
        sev = "med"
    elif delta >= 20:
        sev = "good"

    direction = "up" if delta >= 0 else "down"
    return [
        Insight(
            id="sales.top_category_mover.30d",
            severity=sev,
            category="sales",
            title=f"Category driver: {top_cat}",
            detail=(
                f"'{top_cat}' revenue is {direction} {abs(delta):.1f}% vs prior 30d "
                f"(${cur_v:,.0f} vs ${prior_v:,.0f})."
            ),
            metric="sales.revenue_total",
            value=cur_v,
            prior_value=prior_v,
            delta_pct=delta,
            unit="currency_usd",
        )
    ]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


CHECKS: tuple[tuple[str, Any], ...] = (
    ("sales_kpis_30d", _check_sales_kpis_30d),
    ("finance_health_30d", _check_finance_health_30d),
    ("inventory_now", _check_inventory_now),
    ("top_category_mover_30d", _check_top_category_mover_30d),
)


async def _run_check_with_retry(name: str, fn: Any) -> list[Insight]:
    """Run one check; if it emits only `unknown` results, retry once after a short
    backoff. Protects against a cold-start / transient connection blip landing on
    the very first invocation after Neon compute wakes."""
    try:
        result = await fn()
    except Exception as e:  # noqa: BLE001
        log.warning("insights.check.raised", check=name, error=str(e))
        result = [
            Insight(
                id=f"insights.{name}.error",
                severity="unknown",
                category="ops",
                title=f"{name} unavailable",
                detail=str(e),
            )
        ]

    # Retry once if every item is "unknown" (typically a PoolTimeout on cold start).
    if result and all(i.severity == "unknown" for i in result):
        log.info("insights.check.retry", check=name)
        await asyncio.sleep(1.0)
        try:
            retry = await fn()
            if retry and not all(i.severity == "unknown" for i in retry):
                return retry
        except Exception as e:  # noqa: BLE001
            log.warning("insights.check.retry_failed", check=name, error=str(e))
    return result


async def compute_insights() -> list[dict[str, Any]]:
    """Run every check in parallel and return a JSON-serialisable list.

    Order is: highest severity first, then the rest in the declaration order
    below. Frontend can group by category if desired.
    """
    # 1) Prewarm the connection pool on a single request so a cold Neon compute
    #    doesn't cause a thundering herd on the parallel fan-out below.
    await _prewarm()

    # 2) Run all checks concurrently, each with its own single retry.
    coros = [_run_check_with_retry(name, fn) for name, fn in CHECKS]
    results = await asyncio.gather(*coros, return_exceptions=True)

    flat: list[Insight] = []
    for r in results:
        if isinstance(r, Exception):
            log.warning("insights.check.failed", error=str(r))
            flat.append(
                Insight(
                    id="insights.check.error",
                    severity="unknown",
                    category="ops",
                    title="Insight check failed",
                    detail=str(r),
                )
            )
            continue
        flat.extend(r)  # type: ignore[arg-type]

    # Stable severity ordering: high -> med -> low -> info -> good -> unknown.
    order = {"high": 0, "med": 1, "low": 2, "info": 3, "good": 4, "unknown": 5}
    flat.sort(key=lambda i: order.get(i.severity, 99))

    return [asdict(i) for i in flat]
