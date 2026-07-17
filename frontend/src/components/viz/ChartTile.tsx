"use client";

import { LineChart } from "lucide-react";

import { MetricChart } from "@/components/chat/tools/MetricChart";
import {
  CompositeKpis,
  QueryPostgresCard,
} from "@/components/chat/tools/ToolResultRouter";
import type {
  CompileCompositeResult,
  CompileMetricResult,
  QueryPostgresResult,
  ToolCallState,
} from "@/lib/types";

interface ChartTileProps {
  call: ToolCallState;
  isLatest?: boolean;
}

/** A single visualization card in the right-hand panel. */
export function ChartTile({ call, isLatest }: ChartTileProps) {
  const title = titleFor(call);
  const subtitle = subtitleFor(call);
  const ts = call.finishedAt ?? call.startedAt;

  return (
    <div
      className={`rounded-xl border bg-card p-4 shadow-sm ${
        isLatest ? "ring-1 ring-primary/20" : ""
      }`}
    >
      <div className="mb-3 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-[11px] uppercase tracking-wide text-muted-foreground">
            <LineChart className="size-3.5" />
            <span>{call.name}</span>
            {isLatest && (
              <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[9px] font-medium text-primary">
                latest
              </span>
            )}
          </div>
          <div className="mt-0.5 truncate text-sm font-medium text-foreground">
            {title}
          </div>
          {subtitle && (
            <div className="mt-0.5 truncate text-[11px] text-muted-foreground">
              {subtitle}
            </div>
          )}
        </div>
        <div className="shrink-0 text-[10px] tabular-nums text-muted-foreground">
          {new Date(ts).toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </div>
      </div>

      <div>{renderBody(call)}</div>
    </div>
  );
}

function renderBody(call: ToolCallState): React.ReactNode {
  const r = call.result;
  if (!r) return null;
  switch (call.name) {
    case "compile_metric":
      return <MetricChart data={r as CompileMetricResult} />;
    case "compile_composite":
      return <CompositeKpis data={r as CompileCompositeResult} />;
    case "query_postgres":
      return <QueryPostgresCard data={r as QueryPostgresResult} />;
    default:
      return null;
  }
}

function titleFor(call: ToolCallState): string {
  const input = (call.input ?? {}) as Record<string, unknown>;
  const result = (call.result ?? {}) as Record<string, unknown>;
  switch (call.name) {
    case "compile_metric": {
      const metric = String(input.metric ?? result.metric ?? "");
      const dims = Array.isArray(input.dimensions) ? (input.dimensions as string[]) : [];
      return dims.length > 0 ? `${metric} · by ${dims.join(", ")}` : metric;
    }
    case "compile_composite": {
      const metrics = Array.isArray(input.metrics)
        ? (input.metrics as Array<{ metric: string }>)
            .map((m) => m.metric)
            .join(", ")
        : "";
      return metrics || "composite";
    }
    case "query_postgres":
      return "SQL query";
    default:
      return call.name;
  }
}

function subtitleFor(call: ToolCallState): string | null {
  const input = (call.input ?? {}) as Record<string, unknown>;
  if (call.name === "query_postgres" && typeof input.sql === "string") {
    return truncate(input.sql.replace(/\s+/g, " ").trim(), 100);
  }
  if (call.name === "compile_metric" && input.filters) {
    try {
      return `filters: ${JSON.stringify(input.filters)}`;
    } catch {
      return null;
    }
  }
  return null;
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}
