"use client";

import { Header } from "@/components/chat/Header";
import { LiveUpdatesPanel } from "@/components/insights/LiveUpdatesPanel";

export default function LiveUpdatesPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header showDocsLink showChatLink showNewChat={false} />
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8">
        <LiveUpdatesPanel />
      </main>
    </div>
  );
}
