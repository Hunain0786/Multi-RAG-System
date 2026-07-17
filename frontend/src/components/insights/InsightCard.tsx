"use client";

import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  CheckCircle2,
  HelpCircle,
  Info,
  Minus,
  TrendingDown,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { ComponentType, SVGProps } from "react";

import { cn } from "@/lib/utils";
import type { Insight, InsightSeverity } from "@/lib/types";

const SEVERITY_STYLES: Record<
  InsightSeverity,
  { label: string; badge: string; ring: string; icon: LucideIcon }
> = {
  high: {
    label: "High",
    badge: "bg-rose-500/12 text-rose-700 ring-rose-500/30",
    ring: "ring-rose-500/40",
    icon: AlertTriangle,
  },
  med: {
    label: "Medium",
    badge: "bg-amber-500/12 text-amber-800 ring-amber-500/30",
    ring: "ring-amber-500/30",
    icon: TrendingDown,
  },
  low: {
    label: "Low",
    badge: "bg-yellow-500/12 text-yellow-800 ring-yellow-500/30",
    ring: "ring-yellow-500/25",
    icon: Info,
  },
  info: {
    label: "Info",
    badge: "bg-slate-500/10 text-slate-700 ring-slate-500/20",
    ring: "ring-slate-500/20",
    icon: Info,
  },
  good: {
    label: "Healthy",
    badge: "bg-emerald-500/12 text-emerald-700 ring-emerald-500/30",
    ring: "ring-emerald-500/25",
    icon: CheckCircle2,
  },
  unknown: {
    label: "Unknown",
    badge: "bg-muted text-muted-foreground ring-border",
    ring: "ring-border",
    icon: HelpCircle,
  },
};

const CATEGORY_LABEL: Record<string, string> = {
  sales: "Sales",
  inventory: "Inventory",
  finance: "Payments",
  hr: "HR",
  ops: "Ops",
};

export function InsightCard({ insight }: { insight: Insight }) {
  const sev = SEVERITY_STYLES[insight.severity] ?? SEVERITY_STYLES.info;
  const Icon = sev.icon;
  const trend = trendIcon(insight);
  const TrendIcon: ComponentType<SVGProps<SVGSVGElement>> | null = trend
    ? trend.icon
    : null;

  return (
    <article
      className={cn(
        "relative flex flex-col gap-3 rounded-xl border bg-card p-4 shadow-sm ring-1 transition hover:shadow-md",
        sev.ring,
      )}
    >
      <header className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2">
          <span
            className={cn(
              "mt-0.5 inline-flex size-8 items-center justify-center rounded-lg ring-1",
              sev.badge,
            )}
            aria-hidden
          >
            <Icon className="size-4" />
          </span>
          <div className="min-w-0">
            <h3 className="text-sm font-semibold leading-tight text-foreground">
              {insight.title}
            </h3>
            <p className="mt-0.5 text-[11px] uppercase tracking-wide text-muted-foreground">
              {CATEGORY_LABEL[insight.category] ?? insight.category}
              {insight.metric && (
                <>
                  {" · "}
                  <code className="font-mono normal-case tracking-normal">
                    {insight.metric}
                  </code>
                </>
              )}
            </p>
          </div>
        </div>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ring-1",
            sev.badge,
          )}
        >
          {sev.label}
        </span>
      </header>

      <p className="text-sm leading-relaxed text-foreground/90">
        {insight.detail}
      </p>

      {(insight.value !== null || insight.delta_pct !== null) && (
        <footer className="mt-auto flex items-end justify-between gap-3 border-t pt-3">
          <div>
            <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
              Current
            </div>
            <div className="text-lg font-semibold tabular-nums text-foreground">
              {formatValue(insight.value, insight.unit ?? null)}
            </div>
          </div>
          {insight.delta_pct !== null && (
            <div
              className={cn(
                "flex items-center gap-1 rounded-full px-2 py-1 text-xs font-medium tabular-nums ring-1",
                trend?.tone ?? "bg-muted text-muted-foreground ring-border",
              )}
              title={
                insight.prior_value !== null
                  ? `Prior: ${formatValue(insight.prior_value, insight.unit ?? null)}`
                  : undefined
              }
            >
              {TrendIcon && <TrendIcon className="size-3.5" />}
              <span>
                {insight.delta_pct > 0 ? "+" : ""}
                {insight.delta_pct.toFixed(1)}%
              </span>
            </div>
          )}
        </footer>
      )}
    </article>
  );
}

function trendIcon(insight: Insight): {
  icon: LucideIcon;
  tone: string;
} | null {
  if (insight.delta_pct === null) return null;
  const pct = insight.delta_pct;
  const isRateMetric =
    insight.unit === "percentage" ||
    /rate|failure|refund|chargeback|cancel/i.test(insight.metric ?? "");
  // For rate-style metrics, up is bad; for volume/currency, down is bad.
  const badWhenUp = isRateMetric;
  if (Math.abs(pct) < 0.5) {
    return { icon: Minus, tone: "bg-muted text-muted-foreground ring-border" };
  }
  if (pct > 0) {
    return badWhenUp
      ? {
          icon: ArrowUpRight,
          tone: "bg-rose-500/10 text-rose-700 ring-rose-500/25",
        }
      : {
          icon: ArrowUpRight,
          tone: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25",
        };
  }
  return badWhenUp
    ? {
        icon: ArrowDownRight,
        tone: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25",
      }
    : {
        icon: ArrowDownRight,
        tone: "bg-rose-500/10 text-rose-700 ring-rose-500/25",
      };
}

function formatValue(v: number | null, unit: string | null): string {
  if (v === null || v === undefined) return "—";
  if (unit === "currency_usd") {
    return v.toLocaleString("en-US", {
      style: "currency",
      currency: "USD",
      maximumFractionDigits: v >= 1000 ? 0 : 2,
    });
  }
  if (unit === "percentage") {
    return `${v.toFixed(2)}%`;
  }
  if (unit === "integer") {
    return Math.round(v).toLocaleString("en-US");
  }
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
}
