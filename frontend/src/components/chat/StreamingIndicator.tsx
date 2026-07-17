"use client";

import type { AssistantChatMessage } from "@/lib/types";

/**
 * Live indicator shown at the tail of a streaming assistant message.
 *
 * The label reflects what the agent is actually doing right now:
 *
 *   - "Thinking"          — no text or tool activity yet
 *   - "Calling <tool>"    — one or more tool_use blocks are still running
 *   - "Writing"           — text tokens are streaming in (last block is text)
 *
 * The dots use a staggered pulse so they visibly animate even when text
 * generation stalls between tokens.
 */

interface StreamingIndicatorProps {
  message: AssistantChatMessage;
}

const TOOL_LABELS: Record<string, string> = {
  compile_metric: "compile_metric",
  compile_composite: "compile_composite",
  list_catalog: "list_catalog",
  list_metrics: "list_metrics",
  search_docs: "search_docs",
  query_postgres: "query_postgres",
  remember: "remember",
  recall: "recall",
  forget: "forget",
};

export function StreamingIndicator({ message }: StreamingIndicatorProps) {
  if (!message.streaming) return null;

  const label = deriveLabel(message);

  return (
    <div
      role="status"
      aria-live="polite"
      className="inline-flex items-center gap-2 rounded-full border bg-muted/50 px-3 py-1 text-[11px] text-muted-foreground shadow-sm"
    >
      <span className="flex items-center gap-1" aria-hidden>
        <span className="size-1.5 animate-[dotpulse_1.2s_ease-in-out_infinite] rounded-full bg-primary/70" />
        <span
          className="size-1.5 animate-[dotpulse_1.2s_ease-in-out_infinite] rounded-full bg-primary/70"
          style={{ animationDelay: "160ms" }}
        />
        <span
          className="size-1.5 animate-[dotpulse_1.2s_ease-in-out_infinite] rounded-full bg-primary/70"
          style={{ animationDelay: "320ms" }}
        />
      </span>
      <span>{label}</span>
    </div>
  );
}

function deriveLabel(m: AssistantChatMessage): string {
  const runningTool = m.toolCalls.find((t) => t.status === "running");
  if (runningTool) {
    const name = TOOL_LABELS[runningTool.name] ?? runningTool.name;
    return `Calling ${name}…`;
  }

  const last = m.blocks[m.blocks.length - 1];
  if (last && last.kind === "text" && last.text.length > 0) {
    return "Writing…";
  }

  return "Thinking…";
}
