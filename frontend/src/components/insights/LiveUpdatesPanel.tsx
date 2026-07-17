"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { getInsights } from "@/lib/api";
import { cn } from "@/lib/utils";
import type {
  Insight,
  InsightCategory,
  InsightSeverity,
  InsightsResponse,
} from "@/lib/types";

import { InsightCard } from "./InsightCard";

type CategoryFilter = "all" | InsightCategory;
type SeverityFilter = "all" | "risk" | InsightSeverity;

const CATEGORY_LABEL: Record<CategoryFilter, string> = {
  all: "All areas",
  sales: "Sales",
  inventory: "Inventory",
  finance: "Payments",
  hr: "HR",
  ops: "Ops",
};

const SEVERITY_LABEL: Record<SeverityFilter, string> = {
  all: "All signals",
  risk: "Risks only",
  high: "High",
  med: "Medium",
  low: "Low",
  info: "Info",
  good: "Healthy",
  unknown: "Unknown",
};

export function LiveUpdatesPanel() {
  const [data, setData] = useState<InsightsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [category, setCategory] = useState<CategoryFilter>("all");
  const [severity, setSeverity] = useState<SeverityFilter>("all");

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await getInsights();
      setData(res);
    } catch (e) {
      const msg = (e as Error).message;
      setError(msg);
      toast.error(`Failed to load insights: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const items: Insight[] = data?.items ?? [];

  const categories = useMemo(() => {
    const set = new Set<CategoryFilter>(["all"]);
    for (const i of items) set.add(i.category as CategoryFilter);
    return Array.from(set);
  }, [items]);

  const filtered = useMemo(() => {
    return items.filter((i) => {
      if (category !== "all" && i.category !== category) return false;
      if (severity === "all") return true;
      if (severity === "risk") return i.severity === "high" || i.severity === "med";
      return i.severity === severity;
    });
  }, [items, category, severity]);

  const counts = data?.counts ?? {
    high: 0,
    med: 0,
    low: 0,
    info: 0,
    good: 0,
    unknown: 0,
  };

  return (
    <section className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            Live Updates
          </h1>
          <p className="mt-1 max-w-2xl text-sm text-muted-foreground">
            Continuously-computed insights and risk signals over your
            operational data. The same analyst rules the agent applies in
            chat — surfaced here so you can scan for things going wrong before
            you ask.
          </p>
          {data?.generated_at && (
            <p className="mt-2 text-[11px] text-muted-foreground">
              Last computed {new Date(data.generated_at).toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => void load()}
            disabled={loading}
            className="gap-1.5"
          >
            {loading ? (
              <Loader2 className="size-4 animate-spin" />
            ) : (
              <RefreshCw className="size-4" />
            )}
            Refresh
          </Button>
        </div>
      </header>

      <div className="flex flex-wrap items-center gap-2">
        <CountPill tone="rose" label="High" count={counts.high} />
        <CountPill tone="amber" label="Medium" count={counts.med} />
        <CountPill tone="yellow" label="Low" count={counts.low} />
        <CountPill tone="emerald" label="Healthy" count={counts.good} />
        <CountPill tone="slate" label="Info" count={counts.info} />
      </div>

      <div className="flex flex-wrap items-center gap-2 border-y py-3">
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Filters
        </span>
        <FilterGroup
          label="Area"
          value={category}
          onChange={(v) => setCategory(v as CategoryFilter)}
          options={categories.map((c) => ({
            value: c,
            label: CATEGORY_LABEL[c] ?? c,
          }))}
        />
        <FilterGroup
          label="Severity"
          value={severity}
          onChange={(v) => setSeverity(v as SeverityFilter)}
          options={(
            ["all", "risk", "high", "med", "low", "info", "good"] as SeverityFilter[]
          ).map((s) => ({ value: s, label: SEVERITY_LABEL[s] }))}
        />
      </div>

      {loading && !data && (
        <div className="flex items-center justify-center gap-2 py-16 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" />
          Computing insights…
        </div>
      )}

      {error && !loading && (
        <div className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-800">
          Could not load insights: {error}
        </div>
      )}

      {!loading && filtered.length === 0 && !error && (
        <div className="rounded-lg border border-dashed p-10 text-center text-sm text-muted-foreground">
          Nothing to show for this filter.
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {filtered.map((i) => (
          <InsightCard key={i.id} insight={i} />
        ))}
      </div>
    </section>
  );
}

function CountPill({
  tone,
  label,
  count,
}: {
  tone: "rose" | "amber" | "yellow" | "emerald" | "slate";
  label: string;
  count: number;
}) {
  const toneClass: Record<typeof tone, string> = {
    rose: "bg-rose-500/10 text-rose-700 ring-rose-500/25",
    amber: "bg-amber-500/10 text-amber-800 ring-amber-500/25",
    yellow: "bg-yellow-500/10 text-yellow-800 ring-yellow-500/25",
    emerald: "bg-emerald-500/10 text-emerald-700 ring-emerald-500/25",
    slate: "bg-slate-500/10 text-slate-700 ring-slate-500/20",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1",
        toneClass[tone],
      )}
    >
      <span className="tabular-nums">{count}</span>
      <span className="opacity-80">{label}</span>
    </span>
  );
}

function FilterGroup({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: Array<{ value: string; label: string }>;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-[11px] text-muted-foreground">{label}:</span>
      <div className="flex flex-wrap gap-1">
        {options.map((o) => (
          <button
            key={o.value}
            type="button"
            onClick={() => onChange(o.value)}
            className={cn(
              "rounded-full border px-2.5 py-0.5 text-xs transition",
              value === o.value
                ? "border-primary bg-primary/10 text-primary"
                : "border-border text-muted-foreground hover:bg-muted",
            )}
          >
            {o.label}
          </button>
        ))}
      </div>
    </div>
  );
}
