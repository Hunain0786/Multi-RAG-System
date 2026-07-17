"use client";

import { useMemo } from "react";
import { BarChart3, Sparkles } from "lucide-react";

import { ChartTile } from "@/components/viz/ChartTile";
import { isChartWorthy } from "@/lib/charts";
import { useConversation } from "@/store/conversation";
import type { ChatMessage, ToolCallState } from "@/lib/types";

/**
 * Right-hand pane: every chart-worthy tool call in this conversation, newest
 * first. The most-recent one gets a subtle highlight ring.
 *
 * The panel owns its own vertical scroll so the chat column and this column
 * can scroll independently without the outer page ever needing to.
 */
export function VisualizationPanel() {
  const messages = useConversation((s) => s.messages);
  const streaming = useConversation((s) => s.streaming);

  const charts = useMemo(() => collectCharts(messages), [messages]);

  return (
    <aside className="hidden h-full min-h-0 flex-col border-l bg-muted/30 md:flex">
      <div className="flex shrink-0 items-center justify-between border-b bg-background/70 px-4 py-3 backdrop-blur">
        <div className="flex items-center gap-2">
          <BarChart3 className="size-4 text-primary" />
          <h2 className="text-sm font-semibold tracking-tight">
            Visualizations
          </h2>
        </div>
        <div className="text-[11px] text-muted-foreground">
          {charts.length === 0
            ? "—"
            : `${charts.length} chart${charts.length === 1 ? "" : "s"}`}
        </div>
      </div>

      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
        {charts.length === 0 ? (
          <EmptyState streaming={streaming} />
        ) : (
          <div className="space-y-4">
            {charts.map((c, idx) => (
              <ChartTile key={c.id} call={c} isLatest={idx === 0} />
            ))}
          </div>
        )}
      </div>
    </aside>
  );
}

function EmptyState({ streaming }: { streaming: boolean }) {
  return (
    <div className="flex h-full flex-col items-center justify-center text-center">
      <div className="rounded-full border bg-card p-3">
        <Sparkles className="size-5 text-primary/70" />
      </div>
      <h3 className="mt-3 text-sm font-medium">
        {streaming ? "Working…" : "Charts appear here"}
      </h3>
      <p className="mt-1 max-w-[26ch] text-xs text-muted-foreground">
        Ask a data question and any metric, composite, or SQL query the agent
        runs will be visualized here.
      </p>
    </div>
  );
}

function collectCharts(messages: ChatMessage[]): ToolCallState[] {
  const out: ToolCallState[] = [];
  for (const m of messages) {
    if (m.role !== "assistant") continue;
    for (const call of m.toolCalls) {
      if (isChartWorthy(call)) out.push(call);
    }
  }
  return out.reverse();
}
