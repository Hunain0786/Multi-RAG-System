/**
 * Chart selection helpers shared between the inline tool card in the chat
 * transcript and the dedicated visualization panel.
 *
 * `compile_metric` already ships a `chart_hint`, so we trust it. For
 * `query_postgres` we infer a reasonable chart shape from the rows:
 *   - single-row numeric      -> kpi
 *   - date-like x column      -> line
 *   - <= 8 categorical groups -> pie
 *   - otherwise               -> bar
 * If we can't find at least one numeric column we return null and the caller
 * should fall back to a table.
 */

import type {
  CompileMetricResult,
  MetricFormat,
  QueryPostgresResult,
  ToolCallState,
} from "@/lib/types";

export function inferFormat(
  rows: Array<Record<string, unknown>>,
  key: string,
): MetricFormat {
  const values = rows
    .map((r) => r[key])
    .filter((v) => v !== null && v !== undefined);
  if (values.length === 0) return "string";
  if (values.every((v) => typeof v === "number")) {
    return values.every((v) => Number.isInteger(v)) ? "integer" : "number";
  }
  return "string";
}

export function isDateLikeString(v: unknown): boolean {
  if (typeof v !== "string") return false;
  if (/^\d{4}-\d{2}(-\d{2})?/.test(v)) return true;
  const parsed = Date.parse(v);
  return !Number.isNaN(parsed);
}

export function buildSqlChartData(
  q: QueryPostgresResult,
): CompileMetricResult | null {
  if (q.rows.length === 0) return null;
  const first = q.rows[0];
  const keys = Object.keys(first);
  if (keys.length === 0) return null;

  const numericKeys = keys.filter((k) =>
    q.rows.every(
      (r) => typeof r[k] === "number" || r[k] === null || r[k] === undefined,
    ),
  );
  if (numericKeys.length === 0) return null;

  const valueKey = numericKeys[0];
  const valueFormat = inferFormat(q.rows, valueKey);
  const xCandidate =
    keys.find((k) => isDateLikeString(first[k])) ??
    keys.find((k) => !numericKeys.includes(k));

  if (q.rows.length === 1 || !xCandidate) {
    return {
      metric: `query_postgres.${valueKey}`,
      domain: "sql",
      columns: [{ name: "value", label: valueKey, format: valueFormat }],
      rows: [{ value: q.rows[0]?.[valueKey] ?? null }],
      sql: q.sql,
      chart_hint: { type: "kpi", x_key: null },
      pagination: {
        limit: q.row_count,
        offset: 0,
        next_offset: q.row_count,
        has_more: false,
        total_returned: q.row_count,
      },
    };
  }

  const chartType: CompileMetricResult["chart_hint"]["type"] = isDateLikeString(
    first[xCandidate],
  )
    ? "line"
    : q.rows.length <= 8
      ? "pie"
      : "bar";

  return {
    metric: `query_postgres.${valueKey}`,
    domain: "sql",
    columns: [
      { name: "dim_1", label: xCandidate, format: "string" },
      { name: "value", label: valueKey, format: valueFormat },
    ],
    rows: q.rows.map((r) => ({
      dim_1: String(r[xCandidate] ?? ""),
      value: r[valueKey] ?? null,
    })),
    sql: q.sql,
    chart_hint: { type: chartType, x_key: "dim_1" },
    pagination: {
      limit: q.row_count,
      offset: 0,
      next_offset: q.row_count,
      has_more: false,
      total_returned: q.row_count,
    },
  };
}

export function inferColumns(
  rows: Array<Record<string, unknown>>,
): Array<{ name: string; label: string; format: MetricFormat }> {
  const first = rows[0];
  if (!first) return [];
  return Object.keys(first).map((k) => ({
    name: k,
    label: k,
    format: inferFormat(rows, k),
  }));
}

/**
 * A tool call from `useConversation.messages` that produced a chart-worthy
 * result. Used by `VisualizationPanel`.
 */
export function isChartWorthy(call: ToolCallState): boolean {
  if (call.status !== "done" || !call.result) return false;
  if (call.name === "compile_metric" || call.name === "compile_composite") {
    return true;
  }
  if (call.name === "query_postgres") {
    const q = call.result as QueryPostgresResult;
    return Array.isArray(q?.rows) && q.rows.length > 0;
  }
  return false;
}
