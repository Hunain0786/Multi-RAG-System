"use client";

import { AlertTriangle, Sparkles } from "lucide-react";

import { Markdown } from "@/components/chat/Markdown";
import { StreamingIndicator } from "@/components/chat/StreamingIndicator";
import { ToolCard } from "@/components/chat/tools/ToolCard";
import type { AssistantChatMessage } from "@/lib/types";

interface AssistantMessageProps {
  message: AssistantChatMessage;
}

export function AssistantMessage({ message }: AssistantMessageProps) {
  const toolById = new Map(message.toolCalls.map((t) => [t.id, t]));

  return (
    <div className="flex gap-3">
      <div className="mt-0.5 flex size-8 shrink-0 items-center justify-center rounded-full border bg-card">
        <Sparkles className="size-4 text-primary" />
      </div>

      <div className="min-w-0 flex-1 space-y-3">
        {message.blocks.map((block, idx) => {
          if (block.kind === "text") {
            const isLast = idx === message.blocks.length - 1;
            return (
              <div key={`t-${idx}`}>
                <Markdown>{block.text}</Markdown>
                {isLast && message.streaming && (
                  <span
                    aria-hidden
                    className="ml-0.5 inline-block h-4 w-[7px] translate-y-0.5 animate-pulse bg-foreground/70 align-middle"
                  />
                )}
              </div>
            );
          }
          const tc = toolById.get(block.toolCallId);
          if (!tc) return null;
          return <ToolCard key={tc.id} call={tc} />;
        })}

        {message.streaming && <StreamingIndicator message={message} />}

        {message.errorText && (
          <div className="flex items-start gap-2 rounded-md border border-destructive/40 bg-destructive/5 px-3 py-2 text-sm text-destructive">
            <AlertTriangle className="mt-0.5 size-4 shrink-0" />
            <span>{message.errorText}</span>
          </div>
        )}
      </div>
    </div>
  );
}
