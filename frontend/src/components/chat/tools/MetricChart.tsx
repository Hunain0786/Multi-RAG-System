"use client";

import { useMemo, useState } from "react";
import type { EChartsOption } from "echarts";
import ReactECharts from "echarts-for-react";

import { SqlResultTable } from "@/components/chat/tools/SqlResultTable";
import { formatCell } from "@/lib/format";
import type { CompileMetricResult, MetricFormat } from "@/lib/types";

/**
 * MetricChart renders a `compile_metric` (or synthesized `query_postgres`)
 * result as an Apache ECharts visualization. Chart type is driven by
 * `chart_hint.type`:
 *
 *   bar   -> categorical bar
 *   line  -> line chart
 *   area  -> line chart with area gradient
 *   pie   -> donut
 *   kpi   -> big-number tile
 *   table -> defers to `SqlResultTable`
 *
 * ECharts sizes itself against its parent, and we always give it a bounded
 * container (`min-h-[16rem]`) so it can never collapse to 0 height in a flex
 * layout.
 */

// ECharts renders via SVG/Canvas and cannot resolve CSS `var()` in fill
// attributes, so we pin the palette here. These match the warm beige-friendly
// tones defined for `--chart-1..5` in globals.css.
const CHART_COLORS = [
  "#B0623E", // terracotta
  "#7A8B4F", // olive
  "#4D6A9E", // dusty blue
  "#C77D5C", // coral
  "#8B6F47", // bronze
];

// Neutral tokens (used for axes / grid / borders inside ECharts). Hex twin of
// the beige CSS variables.
const NEUTRAL = {
  border: "#DFD3B8",
  muted: "#EDE3CD",
  mutedFg: "#7A6B54",
  fg: "#3A2F20",
  card: "#FFFFFF",
};

interface MetricChartProps {
  data: CompileMetricResult;
}

export function MetricChart({ data }: MetricChartProps) {
  const { chart_hint, rows, columns, sql, metric, pagination } = data;

  const [tab, setTab] = useState<"chart" | "table">(pickInitialTab(data));

  const valueCol = columns.find((c) => c.name === "value");
  const valueFormat: MetricFormat = valueCol?.format ?? "number";
  const xKey = chart_hint.x_key ?? "dim_1";
  const xCol = columns.find((c) => c.name === xKey);

  // KPI: single number, no dimensions.
  if (chart_hint.type === "kpi" || rows.length === 0) {
    const value = rows[0]?.value ?? null;
    return (
      <div className="space-y-3">
        <div className="rounded-md border bg-card px-4 py-4">
          <div className="text-[10px] uppercase tracking-wide text-muted-foreground">
            {valueCol?.label ?? metric}
          </div>
          <div className="mt-1 text-3xl font-semibold tabular-nums">
            {formatCell(value, valueFormat)}
          </div>
        </div>
        {sql && <SqlDisclosure sql={sql} />}
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
        <div className="rounded-md border bg-card p-2">
          <EChartsBody
            data={data}
            xKey={xKey}
            xLabel={xCol?.label ?? xKey}
            yLabel={valueCol?.label ?? "value"}
            valueFormat={valueFormat}
          />
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

function SqlDisclosure({ sql }: { sql: string }) {
  return (
    <details className="rounded-md border bg-muted/40 text-[11px]">
      <summary className="cursor-pointer px-2 py-1 text-muted-foreground">
        SQL
      </summary>
      <pre className="overflow-x-auto p-2 font-mono">{sql}</pre>
    </details>
  );
}

interface EChartsBodyProps {
  data: CompileMetricResult;
  xKey: string;
  xLabel: string;
  yLabel: string;
  valueFormat: MetricFormat;
}

function EChartsBody({
  data,
  xKey,
  xLabel,
  yLabel,
  valueFormat,
}: EChartsBodyProps) {
  const option = useMemo<EChartsOption>(
    () => buildOption(data, xKey, xLabel, yLabel, valueFormat),
    [data, xKey, xLabel, yLabel, valueFormat],
  );

  return (
    <ReactECharts
      option={option}
      style={{ height: "18rem", width: "100%" }}
      opts={{ renderer: "svg" }}
      notMerge
      lazyUpdate
    />
  );
}

function buildOption(
  data: CompileMetricResult,
  xKey: string,
  xLabel: string,
  yLabel: string,
  valueFormat: MetricFormat,
): EChartsOption {
  const { chart_hint, rows } = data;

  const categories = rows.map((r) => truncate(String(r[xKey] ?? ""), 20));
  const values = rows.map((r) => toNumber(r["value"]));

  const fmt = (v: number | string | null | undefined): string =>
    formatCell(v, valueFormat);

  const tooltip: EChartsOption["tooltip"] = {
    trigger: chart_hint.type === "pie" ? "item" : "axis",
    backgroundColor: NEUTRAL.card,
    borderColor: NEUTRAL.border,
    borderWidth: 1,
    textStyle: {
      color: NEUTRAL.fg,
      fontSize: 12,
    },
    formatter: (params) => {
      const list = Array.isArray(params) ? params : [params];
      const rowsHtml = list
        .map((p) => {
          const value = Array.isArray(p.value)
            ? (p.value as unknown[])[1]
            : (p.value as number | null | undefined);
          const label = String(p.name ?? "");
          return `
            <div style="display:flex;align-items:center;gap:6px;">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};"></span>
              <span style="color:${NEUTRAL.mutedFg};">${escapeHtml(label)}</span>
              <span style="margin-left:auto;font-variant-numeric:tabular-nums;">${escapeHtml(fmt(value as number))}</span>
            </div>`;
        })
        .join("");
      return `<div style="min-width:150px;font-size:12px;">
                <div style="margin-bottom:4px;font-size:11px;color:${NEUTRAL.mutedFg};">${escapeHtml(xLabel)}</div>
                ${rowsHtml}
              </div>`;
    },
  };

  const grid: EChartsOption["grid"] = {
    top: 24,
    right: 16,
    bottom: 40,
    left: 56,
    containLabel: true,
  };

  const xAxis: EChartsOption["xAxis"] = {
    type: "category",
    data: categories,
    axisLabel: {
      color: NEUTRAL.mutedFg,
      fontSize: 11,
      interval: 0,
      rotate: categories.some((c) => c.length > 10) ? 20 : 0,
    },
    axisLine: { lineStyle: { color: NEUTRAL.border } },
    axisTick: { alignWithLabel: true },
  };

  const yAxis: EChartsOption["yAxis"] = {
    type: "value",
    name: yLabel,
    nameTextStyle: {
      color: NEUTRAL.mutedFg,
      fontSize: 11,
      padding: [0, 0, 0, 40],
    },
    axisLabel: {
      color: NEUTRAL.mutedFg,
      fontSize: 11,
      formatter: (v: number) => compactNumber(v),
    },
    splitLine: {
      lineStyle: { color: NEUTRAL.border, type: "dashed", opacity: 0.6 },
    },
  };

  switch (chart_hint.type) {
    case "pie":
      return {
        tooltip,
        legend: {
          bottom: 0,
          type: "scroll",
          textStyle: {
            color: NEUTRAL.mutedFg,
            fontSize: 11,
          },
        },
        color: CHART_COLORS,
        series: [
          {
            type: "pie",
            radius: ["45%", "72%"],
            avoidLabelOverlap: true,
            itemStyle: {
              borderColor: NEUTRAL.card,
              borderWidth: 2,
              borderRadius: 4,
            },
            label: { show: false },
            emphasis: {
              label: {
                show: true,
                fontSize: 13,
                fontWeight: 600,
                color: NEUTRAL.fg,
                formatter: (p) => {
                  const raw = (p as { name?: unknown; value?: unknown }).value;
                  const n = typeof raw === "number" ? raw : toNumber(raw);
                  return `${(p as { name?: string }).name ?? ""}\n${fmt(n)}`;
                },
              },
            },
            data: rows.map((r, i) => ({
              name: truncate(String(r[xKey] ?? ""), 24),
              value: toNumber(r["value"]),
              itemStyle: { color: CHART_COLORS[i % CHART_COLORS.length] },
            })),
          },
        ],
      };

    case "line":
    case "area":
      return {
        tooltip,
        grid,
        xAxis,
        yAxis,
        color: CHART_COLORS,
        series: [
          {
            type: "line",
            name: yLabel,
            data: values,
            smooth: true,
            symbol: "circle",
            symbolSize: 6,
            lineStyle: { width: 2 },
            areaStyle:
              chart_hint.type === "area"
                ? {
                    color: {
                      type: "linear",
                      x: 0,
                      y: 0,
                      x2: 0,
                      y2: 1,
                      colorStops: [
                        { offset: 0, color: withAlpha(CHART_COLORS[0], 0.35) },
                        { offset: 1, color: withAlpha(CHART_COLORS[0], 0) },
                      ],
                    },
                  }
                : undefined,
          },
        ],
      };

    case "bar":
    default:
      return {
        tooltip,
        grid,
        xAxis,
        yAxis,
        color: CHART_COLORS,
        series: [
          {
            type: "bar",
            name: yLabel,
            data: values.map((v, i) => ({
              value: v,
              itemStyle: {
                color: CHART_COLORS[i % CHART_COLORS.length],
                borderRadius: [4, 4, 0, 0],
              },
            })),
            barMaxWidth: 40,
          },
        ],
      };
  }
}

function toNumber(v: unknown): number {
  if (typeof v === "number") return v;
  if (typeof v === "string") {
    const n = parseFloat(v);
    return Number.isFinite(n) ? n : 0;
  }
  return 0;
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}

function compactNumber(v: number): string {
  const abs = Math.abs(v);
  if (abs >= 1_000_000_000) return `${(v / 1_000_000_000).toFixed(1)}B`;
  if (abs >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${(v / 1_000).toFixed(1)}K`;
  return String(v);
}

function withAlpha(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
