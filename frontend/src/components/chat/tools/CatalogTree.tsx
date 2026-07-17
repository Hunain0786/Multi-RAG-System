"use client";

import { useMemo } from "react";
import { BarChart3, LineChart, PieChart as PieIcon, Gauge, Table as TableIcon, AreaChart as AreaIcon } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { ChartType, ListMetricsResult, MetricCatalogEntry } from "@/lib/types";

const CHART_ICON: Record<ChartType, React.ComponentType<{ className?: string }>> = {
  bar: BarChart3,
  line: LineChart,
  area: AreaIcon,
  pie: PieIcon,
  kpi: Gauge,
  table: TableIcon,
};

interface CatalogTreeProps {
  data: ListMetricsResult;
}

export function CatalogTree({ data }: CatalogTreeProps) {
  const grouped = useMemo(() => {
    const g = new Map<string, MetricCatalogEntry[]>();
    for (const m of data.metrics) {
      if (!g.has(m.domain)) g.set(m.domain, []);
      g.get(m.domain)!.push(m);
    }
    return Array.from(g.entries()).sort((a, b) => a[0].localeCompare(b[0]));
  }, [data.metrics]);

  return (
    <div className="space-y-3">
      {grouped.map(([domain, metrics]) => (
        <div key={domain} className="rounded-md border bg-background">
          <div className="border-b bg-muted/40 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted-foreground">
            {domain}
          </div>
          <ul className="divide-y">
            {metrics.map((m) => {
              const Icon = CHART_ICON[m.chart_hint.type] ?? TableIcon;
              return (
                <li key={`${domain}.${m.name}`} className="px-3 py-2 text-[13px]">
                  <div className="flex items-center gap-2">
                    <Icon className="size-3.5 shrink-0 text-muted-foreground" />
                    <span className="font-mono">
                      {domain}.{m.name}
                    </span>
                    <Badge variant="outline" className="text-[10px]">
                      {m.format}
                    </Badge>
                  </div>
                  {m.description && (
                    <p className="mt-1 pl-5 text-[12px] text-muted-foreground">
                      {m.description}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
