"use client";

import { Header } from "@/components/chat/Header";
import { MemoryTable } from "@/components/memory/MemoryTable";

export default function MemoryPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header showDocsLink showChatLink showNewChat={false} />
      <main className="mx-auto w-full max-w-4xl flex-1 space-y-8 px-4 py-8">
        <section className="space-y-2">
          <h1 className="text-xl font-semibold tracking-tight">Memory</h1>
          <p className="text-sm text-muted-foreground">
            Facts the agent has been told to remember across conversations.
            Written explicitly by the <code className="font-mono">remember</code>{" "}
            tool; the agent semantically recalls the most relevant few at the
            start of each turn.
          </p>
        </section>

        <section>
          <MemoryTable />
        </section>
      </main>
    </div>
  );
}
