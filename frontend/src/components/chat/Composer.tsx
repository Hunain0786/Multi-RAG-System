"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { useConversation } from "@/store/conversation";

const MAX_ROWS = 8;
const LINE_HEIGHT_PX = 22;

interface ComposerProps {
  autofocus?: boolean;
}

export function Composer({ autofocus = true }: ComposerProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement>(null);
  const streaming = useConversation((s) => s.streaming);
  const send = useConversation((s) => s.send);
  const abort = useConversation((s) => s.abort);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.style.height = "auto";
    const cap = LINE_HEIGHT_PX * MAX_ROWS + 24;
    el.style.height = `${Math.min(el.scrollHeight, cap)}px`;
    el.style.overflowY = el.scrollHeight > cap ? "auto" : "hidden";
  }, [value]);

  useEffect(() => {
    if (autofocus) ref.current?.focus();
  }, [autofocus]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && streaming) {
        e.preventDefault();
        abort();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [abort, streaming]);

  const doSend = () => {
    const trimmed = value.trim();
    if (!trimmed || streaming) return;
    setValue("");
    void send(trimmed);
  };

  return (
    <div className="bg-background/90 backdrop-blur">
      <div className="mx-auto flex w-full max-w-3xl items-end gap-2 px-4 py-3">
        <div className="flex-1 rounded-2xl border bg-card px-3 py-2 shadow-sm focus-within:border-primary/40 focus-within:ring-1 focus-within:ring-ring/40">
          <Textarea
            ref={ref}
            rows={1}
            placeholder="Ask about your data or your docs…"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                doSend();
              } else if (
                e.key === "Enter" &&
                (e.metaKey || e.ctrlKey)
              ) {
                e.preventDefault();
                doSend();
              }
            }}
            className="min-h-0 resize-none border-0 bg-transparent p-0 text-[15px] leading-[22px] shadow-none focus-visible:ring-0 focus-visible:ring-offset-0"
            aria-label="Message"
          />
        </div>

        {streaming ? (
          <Button
            type="button"
            variant="secondary"
            size="icon"
            className="size-10 shrink-0 rounded-full"
            onClick={abort}
            aria-label="Stop"
          >
            <Square className="size-4" />
          </Button>
        ) : (
          <Button
            type="button"
            size="icon"
            className="size-10 shrink-0 rounded-full"
            onClick={doSend}
            disabled={value.trim().length === 0}
            aria-label="Send"
          >
            <ArrowUp className="size-4" />
          </Button>
        )}
      </div>
      <div className="mx-auto max-w-3xl px-4 pb-3 text-[11px] text-muted-foreground">
        Enter to send · Shift+Enter for newline · Esc to stop
      </div>
    </div>
  );
}
