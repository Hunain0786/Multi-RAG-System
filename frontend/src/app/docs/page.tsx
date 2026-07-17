"use client";

import { Terminal } from "lucide-react";

import { Header } from "@/components/chat/Header";
import { DocsTable } from "@/components/docs/DocsTable";

export default function DocsPage() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header showDocsLink={false} showChatLink showNewChat={false} />
      <main className="mx-auto w-full max-w-4xl flex-1 space-y-8 px-4 py-8">
        <section className="space-y-2">
          <h1 className="text-xl font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Library of documents currently indexed in Pinecone. The agent&apos;s{" "}
            <code className="font-mono">search_docs</code> tool retrieves chunks
            from here.
          </p>
        </section>

        <section className="flex items-start gap-3 rounded-md border border-dashed bg-muted/20 p-4 text-sm">
          <div className="mt-0.5 rounded-full bg-muted p-1.5 text-muted-foreground">
            <Terminal className="size-4" />
          </div>
          <div className="space-y-1.5">
            <div className="font-medium">Ingestion is code-only</div>
            <p className="text-muted-foreground">
              To keep the corpus curated, uploading through the UI is disabled.
              Add files to <code className="font-mono">backend/docs/</code> and
              run one of:
            </p>
            <pre className="mt-1 overflow-x-auto rounded bg-background px-3 py-2 font-mono text-[12px] leading-5">
{`make ingest                                        # ingest every file under backend/docs
python -m multirag.rag.pipeline path/to/file.pdf   # ingest a single file`}
            </pre>
          </div>
        </section>

        <section>
          <h2 className="mb-3 text-sm font-medium">Library</h2>
          <DocsTable refreshKey={0} />
        </section>
      </main>
    </div>
  );
}
