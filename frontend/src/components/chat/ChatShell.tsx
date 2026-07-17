"use client";

import { Composer } from "@/components/chat/Composer";
import { ExamplePrompts } from "@/components/chat/ExamplePrompts";
import { Header } from "@/components/chat/Header";
import { MessageList } from "@/components/chat/MessageList";
import { VisualizationPanel } from "@/components/viz/VisualizationPanel";
import { useConversation } from "@/store/conversation";

/**
 * Full-page chat layout.
 *   - Header spans the top.
 *   - Below the header: a 60/40 grid — chat on the left, visualizations on the
 *     right (`md:grid-cols-[3fr_2fr]`).
 *   - Both columns own their own vertical scroll so neither can push the
 *     window scroll; the composer stays anchored at the bottom of its column.
 */
export function ChatShell() {
  const messages = useConversation((s) => s.messages);
  const send = useConversation((s) => s.send);
  const empty = messages.length === 0;

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background">
      <Header />

      <div className="grid min-h-0 flex-1 grid-cols-1 md:grid-cols-[3fr_2fr]">
        <section className="flex min-h-0 flex-col bg-background">
          <div className="min-h-0 flex-1 overflow-y-auto">
            {empty ? (
              <div className="flex min-h-full items-center justify-center">
                <ExamplePrompts onPick={(p) => void send(p)} />
              </div>
            ) : (
              <MessageList />
            )}
          </div>
          <div className="shrink-0 border-t bg-background">
            <Composer />
          </div>
        </section>

        <VisualizationPanel />
      </div>
    </div>
  );
}
