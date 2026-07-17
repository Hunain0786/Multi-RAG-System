"use client";

import { useState } from "react";
import {
  AlertCircle,
  Braces,
  Check,
  ChevronDown,
  ChevronRight,
  Loader2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ToolResultRouter } from "@/components/chat/tools/ToolResultRouter";
import { formatDurationMs } from "@/lib/format";
import type { ToolCallState } from "@/lib/types";

interface ToolCardProps {
  call: ToolCallState;
}

const TOOL_LABEL: Record<string, string> = {
  compile_metric: "compile_metric",
  compile_composite: "compile_composite",
  search_docs: "search_docs",
  list_catalog: "list_catalog",
  list_metrics: "list_metrics",
  query_postgres: "query_postgres",
  remember: "remember",
  recall: "recall",
  forget: "forget",
};

export function ToolCard({ call }: ToolCardProps) {
  // Auto-expand the moment the result arrives so the user sees fresh output.
  const [expanded, setExpanded] = useState(true);
  const [showRaw, setShowRaw] = useState(false);

  const StatusIcon =
    call.status === "running"
      ? Loader2
      : call.status === "error"
        ? AlertCircle
        : Check;
  const statusClass =
    call.status === "running"
      ? "text-muted-foreground animate-spin"
      : call.status === "error"
        ? "text-destructive"
        : "text-emerald-500";
  const duration =
    call.finishedAt !== undefined
      ? formatDurationMs(call.finishedAt - call.startedAt)
      : null;

  return (
    <div className="rounded-lg border bg-card/50 text-sm shadow-sm">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left hover:bg-accent/30"
      >
        {expanded ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" />
        )}
        <StatusIcon className={`size-4 shrink-0 ${statusClass}`} />
        <Badge variant="secondary" className="font-mono">
          {TOOL_LABEL[call.name] ?? call.name}
        </Badge>
        <span className="ml-1 truncate text-xs text-muted-foreground">
          {summarizeInput(call.name, call.input)}
        </span>
        {duration && (
          <span className="ml-auto shrink-0 text-[11px] tabular-nums text-muted-foreground">
            {duration}
          </span>
        )}
      </button>

      {expanded && (
        <div className="border-t px-3 py-3">
          {call.status === "running" && (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <Loader2 className="size-3.5 animate-spin" />
              Running…
            </div>
          )}
          {call.status === "error" && (
            <div className="rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {call.errorText ?? "Tool call failed."}
            </div>
          )}
          {call.status === "done" && (
            <>
              {showRaw ? (
                <pre className="max-h-80 overflow-auto rounded-md border bg-muted/50 p-3 font-mono text-[11px] leading-5">
                  {JSON.stringify(call.result, null, 2)}
                </pre>
              ) : (
                <ToolResultRouter call={call} />
              )}
              <div className="mt-2 flex justify-end">
                <Button
                  variant="ghost"
                  size="sm"
                  className="h-7 gap-1.5 text-[11px] text-muted-foreground"
                  onClick={() => setShowRaw((v) => !v)}
                >
                  <Braces className="size-3.5" />
                  {showRaw ? "Show rendered" : "Raw JSON"}
                </Button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function summarizeInput(name: string, input: unknown): string {
  if (!input || typeof input !== "object") return "";
  const rec = input as Record<string, unknown>;
  switch (name) {
    case "compile_metric":
      return [
        rec.metric,
        Array.isArray(rec.dimensions) && rec.dimensions.length > 0
          ? `by ${(rec.dimensions as string[]).join(", ")}`
          : "",
        rec.filters ? "· filtered" : "",
      ]
        .filter(Boolean)
        .join(" ");
    case "compile_composite":
      return Array.isArray(rec.metrics)
        ? `${(rec.metrics as Array<{ metric: string }>).map((m) => m.metric).join(", ")}`
        : "";
    case "search_docs":
      return typeof rec.query === "string" ? `"${truncate(rec.query, 60)}"` : "";
    case "query_postgres":
      return typeof rec.sql === "string" ? truncate(rec.sql, 70) : "";
    case "remember":
      return [
        rec.kind ? `[${rec.kind}]` : "",
        typeof rec.text === "string" ? `"${truncate(rec.text, 60)}"` : "",
      ]
        .filter(Boolean)
        .join(" ");
    case "recall":
      return typeof rec.query === "string" ? `"${truncate(rec.query, 60)}"` : "";
    case "forget":
      return typeof rec.id === "string" ? rec.id : "";
    default:
      return "";
  }
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}
