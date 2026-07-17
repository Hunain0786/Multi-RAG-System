"use client";

import { useEffect, useRef } from "react";

import { AssistantMessage } from "@/components/chat/AssistantMessage";
import { UserMessage } from "@/components/chat/UserMessage";
import { useConversation } from "@/store/conversation";

/**
 * Renders the chat transcript. The parent is expected to be a bounded scroll
 * container (see `ChatShell`), so we scroll *within* that container by
 * calling `scrollIntoView` on a bottom sentinel — this never scrolls the
 * page/window.
 */
export function MessageList() {
  const messages = useConversation((s) => s.messages);
  const streaming = useConversation((s) => s.streaming);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll on every new message, every streaming toggle, and any streaming
  // content growth (blocks/toolCalls change identity so `messages` reference
  // updates every SSE event).
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streaming]);

  // While streaming, keep pinning the view to the bottom in case chart tiles
  // grow in height after data arrives.
  useEffect(() => {
    if (!streaming) return;
    const id = window.setInterval(() => {
      bottomRef.current?.scrollIntoView({ behavior: "auto", block: "end" });
    }, 400);
    return () => window.clearInterval(id);
  }, [streaming]);

  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-6">
      {messages.map((m) =>
        m.role === "user" ? (
          <UserMessage key={m.id} message={m} />
        ) : (
          <AssistantMessage key={m.id} message={m} />
        ),
      )}
      <div ref={bottomRef} className="h-px" />
    </div>
  );
}
