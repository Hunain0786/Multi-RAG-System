"use client";

import { useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Legend,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { SqlResultTable } from "@/components/chat/tools/SqlResultTable";
import { formatCell } from "@/lib/format";
import type { CompileMetricResult } from "@/lib/types";

const CHART_COLORS = [
  "var(--color-chart-1)",
  "var(--color-chart-2)",
  "var(--color-chart-3)",
  "var(--color-chart-4)",
  "var(--color-chart-5)",
];

interface MetricChartProps {
  data: CompileMetricResult;
}

export function MetricChart({ data }: MetricChartProps) {
  const { chart_hint, rows, columns, sql, metric, pagination } = data;
  const [tab, setTab] = useState<"chart" | "table">(
    pickInitialTab(data),
  );

  const valueCol = columns.find((c) => c.name === "value");
  const valueFormat = valueCol?.format ?? "number";
  const xKey = chart_hint.x_key ?? "dim_1";
  const xCol = columns.find((c) => c.name === xKey);

  // KPI: single number, no dimensions.
  if (chart_hint.type === "kpi" || rows.length === 0) {
    const value = rows[0]?.value ?? null;
    return (
      <div className="space-y-3">
        <div className="rounded-md border bg-background px-4 py-3">
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {valueCol?.label ?? metric}
          </div>
          <div className="mt-1 text-2xl font-semibold tabular-nums">
            {formatCell(value, valueFormat)}
          </div>
        </div>
        {sql && (
          <details className="rounded-md border bg-muted/20 text-[11px]">
            <summary className="cursor-pointer px-2 py-1 text-muted-foreground">
              SQL
            </summary>
            <pre className="overflow-x-auto p-2 font-mono">{sql}</pre>
          </details>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="text-[11px] text-muted-foreground">
          {metric} · {rows.length} row{rows.length === 1 ? "" : "s"}
          {pagination.has_more && " · more available"}
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
        <div className="h-72 w-full rounded-md border bg-background p-2">
          <ResponsiveContainer width="100%" height="100%">
            {renderChart(data, xKey, xCol?.label ?? xKey, valueCol?.label ?? "value", valueFormat)}
          </ResponsiveContainer>
        </div>
      ) : (
        <SqlResultTable columns={columns} rows={rows} sql={sql} />
      )}
    </div>
  );
}

function pickInitialTab({ chart_hint, rows }: CompileMetricResult): "chart" | "table" {
  if (chart_hint.type === "table") return "table";
  if (rows.length <= 1) return "table";
  return "chart";
}

function renderChart(
  data: CompileMetricResult,
  xKey: string,
  xLabel: string,
  yLabel: string,
  valueFormat: CompileMetricResult["columns"][number]["format"],
) {
  const { chart_hint, rows } = data;

  const tooltipFormatter = (v: unknown): string =>
    formatCell(v, valueFormat);
  const xTick = (v: unknown) =>
    typeof v === "string" && v.length > 14 ? `${v.slice(0, 13)}…` : String(v);

  switch (chart_hint.type) {
    case "line":
      return (
        <LineChart data={rows} margin={{ top: 10, right: 12, bottom: 20, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis
            dataKey={xKey}
            tickFormatter={xTick}
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            stroke="var(--color-border)"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            stroke="var(--color-border)"
            width={60}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(l) => `${xLabel}: ${l}`}
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Line
            type="monotone"
            dataKey="value"
            name={yLabel}
            stroke={CHART_COLORS[0]}
            strokeWidth={2}
            dot={{ r: 3 }}
          />
        </LineChart>
      );

    case "area":
      return (
        <AreaChart data={rows} margin={{ top: 10, right: 12, bottom: 20, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis
            dataKey={xKey}
            tickFormatter={xTick}
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            stroke="var(--color-border)"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            stroke="var(--color-border)"
            width={60}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(l) => `${xLabel}: ${l}`}
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Area
            type="monotone"
            dataKey="value"
            name={yLabel}
            stroke={CHART_COLORS[0]}
            fill={CHART_COLORS[0]}
            fillOpacity={0.2}
          />
        </AreaChart>
      );

    case "pie":
      return (
        <PieChart>
          <Tooltip
            formatter={tooltipFormatter}
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Legend wrapperStyle={{ fontSize: 11 }} />
          <Pie
            data={rows}
            dataKey="value"
            nameKey={xKey}
            innerRadius={40}
            outerRadius={90}
            paddingAngle={1}
          >
            {rows.map((_, i) => (
              <Cell
                key={i}
                fill={CHART_COLORS[i % CHART_COLORS.length]}
              />
            ))}
          </Pie>
        </PieChart>
      );

    case "bar":
    default:
      return (
        <BarChart data={rows} margin={{ top: 10, right: 12, bottom: 20, left: 0 }}>
          <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" />
          <XAxis
            dataKey={xKey}
            tickFormatter={xTick}
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            stroke="var(--color-border)"
          />
          <YAxis
            tick={{ fontSize: 11, fill: "var(--color-muted-foreground)" }}
            stroke="var(--color-border)"
            width={60}
          />
          <Tooltip
            formatter={tooltipFormatter}
            labelFormatter={(l) => `${xLabel}: ${l}`}
            contentStyle={{
              background: "var(--color-popover)",
              border: "1px solid var(--color-border)",
              borderRadius: 6,
              fontSize: 12,
            }}
          />
          <Bar dataKey="value" name={yLabel} radius={[3, 3, 0, 0]}>
            {rows.map((_, i) => (
              <Cell
                key={i}
                fill={CHART_COLORS[i % CHART_COLORS.length]}
              />
            ))}
          </Bar>
        </BarChart>
      );
  }
}
