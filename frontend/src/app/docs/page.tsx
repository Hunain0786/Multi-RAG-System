"use client";

import { useState } from "react";

import { Header } from "@/components/chat/Header";
import { DocUpload } from "@/components/docs/DocUpload";
import { DocsTable } from "@/components/docs/DocsTable";

export default function DocsPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="flex min-h-screen flex-col">
      <Header showChatLink showNewChat={false} />
      <main className="mx-auto w-full max-w-4xl flex-1 space-y-8 px-4 py-8">
        <section className="space-y-2">
          <h1 className="text-xl font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload policies, manuals, and FAQs. The agent&apos;s{" "}
            <code className="font-mono">search_docs</code> tool retrieves chunks
            from this library.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-sm font-medium">Upload</h2>
          <DocUpload onIngested={() => setRefreshKey((k) => k + 1)} />
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium">Library</h2>
          <DocsTable refreshKey={refreshKey} />
        </section>
      </main>
    </div>
  );
}
