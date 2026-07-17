"use client";

import { useMemo, useState } from "react";

import { CatalogTree } from "@/components/chat/tools/CatalogTree";
import { DocChunks } from "@/components/chat/tools/DocChunks";
import {
  ForgetCard,
  RecallCard,
  RememberCard,
} from "@/components/chat/tools/MemoryCards";
import { MetricChart } from "@/components/chat/tools/MetricChart";
import { SqlResultTable } from "@/components/chat/tools/SqlResultTable";
import { buildSqlChartData, inferColumns } from "@/lib/charts";
import { formatCell } from "@/lib/format";
import type {
  CompileCompositeResult,
  CompileMetricResult,
  ForgetResult,
  ListCatalogResult,
  ListMetricsResult,
  QueryPostgresResult,
  RecallResult,
  RememberResult,
  SearchDocsResult,
  ToolCallState,
} from "@/lib/types";

interface Props {
  call: ToolCallState;
}

export function ToolResultRouter({ call }: Props) {
  if (!call.result) {
    return (
      <div className="text-xs text-muted-foreground">(empty result)</div>
    );
  }

  const r = call.result as Record<string, unknown>;

  switch (call.name) {
    case "compile_metric":
      return <MetricChart data={r as unknown as CompileMetricResult} />;

    case "compile_composite":
      return <CompositeKpis data={r as unknown as CompileCompositeResult} />;

    case "query_postgres":
      return <QueryPostgresCard data={r as unknown as QueryPostgresResult} />;

    case "search_docs":
      return <DocChunks data={r as unknown as SearchDocsResult} />;

    case "list_catalog": {
      const cat = (r as unknown as ListCatalogResult).catalog;
      return (
        <pre className="max-h-96 overflow-auto whitespace-pre-wrap rounded-md border bg-muted/40 p-3 font-mono text-[12px] leading-5">
          {cat}
        </pre>
      );
    }

    case "list_metrics":
      return <CatalogTree data={r as unknown as ListMetricsResult} />;

    case "remember":
      return <RememberCard data={r as unknown as RememberResult} />;

    case "recall":
      return <RecallCard data={r as unknown as RecallResult} />;

    case "forget":
      return <ForgetCard data={r as unknown as ForgetResult} />;

    default:
      return (
        <pre className="max-h-80 overflow-auto rounded-md border bg-muted/40 p-3 font-mono text-[11px] leading-5">
          {JSON.stringify(r, null, 2)}
        </pre>
      );
  }
}

export function CompositeKpis({ data }: { data: CompileCompositeResult }) {
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {data.columns.map((c) => {
          const v = data.row[c.name];
          return (
            <div
              key={c.name}
              className="rounded-md border bg-card px-3 py-2"
            >
              <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
                {c.label}
              </div>
              <div className="mt-1 truncate text-xl font-semibold tabular-nums">
                {formatCell(v, c.format)}
              </div>
            </div>
          );
        })}
      </div>
      {data.sql && (
        <details className="rounded-md border bg-muted/40 text-[11px]">
          <summary className="cursor-pointer px-2 py-1 text-muted-foreground">
            SQL
          </summary>
          <pre className="overflow-x-auto p-2 font-mono">{data.sql}</pre>
        </details>
      )}
    </div>
  );
}

export function QueryPostgresCard({ data }: { data: QueryPostgresResult }) {
  const [tab, setTab] = useState<"chart" | "table">("chart");
  const inferred = useMemo(() => inferColumns(data.rows), [data.rows]);
  const chartData = useMemo(() => buildSqlChartData(data), [data]);

  if (!chartData) {
    return (
      <div className="space-y-2">
        <div className="text-[11px] text-muted-foreground">
          {data.row_count} row{data.row_count === 1 ? "" : "s"}
        </div>
        <SqlResultTable columns={inferred} rows={data.rows} sql={data.sql} />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[11px] text-muted-foreground">
          query_postgres · {data.row_count} row{data.row_count === 1 ? "" : "s"}
        </div>
        <div className="flex overflow-hidden rounded-md border text-[11px]">
          <button
            type="button"
            onClick={() => setTab("chart")}
            className={`px-2 py-0.5 ${
              tab === "chart"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent/50"
            }`}
          >
            Chart
          </button>
          <button
            type="button"
            onClick={() => setTab("table")}
            className={`px-2 py-0.5 ${
              tab === "table"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-accent/50"
            }`}
          >
            Table
          </button>
        </div>
      </div>
      {tab === "chart" ? (
        <MetricChart data={chartData} />
      ) : (
        <SqlResultTable columns={inferred} rows={data.rows} sql={data.sql} />
      )}
    </div>
  );
}
