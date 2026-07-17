"use client";

import { useState } from "react";
import { FileText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import type { DocType, SearchDocsResult, SearchHit } from "@/lib/types";

const DOC_TYPE_COLORS: Record<DocType, string> = {
  policy: "bg-[--color-chart-1]/15 text-[--color-chart-1]",
  manual: "bg-[--color-chart-2]/15 text-[--color-chart-2]",
  faq: "bg-[--color-chart-3]/15 text-[--color-chart-3]",
  other: "bg-muted text-muted-foreground",
};

interface DocChunksProps {
  data: SearchDocsResult;
}

export function DocChunks({ data }: DocChunksProps) {
  if (data.hits.length === 0) {
    return (
      <div className="rounded-md border bg-muted/30 px-3 py-6 text-center text-xs text-muted-foreground">
        No matching chunks for {data.query ? `"${data.query}"` : "your query"}.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="text-[11px] text-muted-foreground">
        {data.hits.length} hit{data.hits.length === 1 ? "" : "s"} for “{data.query}”
      </div>
      <div className="space-y-2">
        {data.hits.map((h) => (
          <DocChunkCard key={`${h.doc_id}-${h.chunk_index}`} hit={h} />
        ))}
      </div>
    </div>
  );
}

function DocChunkCard({ hit }: { hit: SearchHit }) {
  const [expanded, setExpanded] = useState(false);
  const TRUNCATE_AT = 380;
  const truncated =
    hit.text.length > TRUNCATE_AT ? `${hit.text.slice(0, TRUNCATE_AT)}…` : hit.text;
  const canExpand = hit.text.length > TRUNCATE_AT;
  const scorePct = Math.max(0, Math.min(1, hit.score));

  return (
    <div className="rounded-md border bg-background p-3">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
        <FileText className="size-3.5 text-muted-foreground" />
        <span className="font-mono text-foreground/90">
          {basename(hit.source_path)}
        </span>
        <span className={`rounded px-1.5 py-0.5 font-medium ${DOC_TYPE_COLORS[hit.doc_type]}`}>
          {hit.doc_type}
        </span>
        <span className="text-muted-foreground">chunk #{hit.chunk_index}</span>
        <span className="ml-auto flex items-center gap-1.5">
          <span className="h-1.5 w-16 overflow-hidden rounded bg-muted">
            <span
              className="block h-full bg-[--color-chart-2]"
              style={{ width: `${scorePct * 100}%` }}
            />
          </span>
          <span className="tabular-nums text-muted-foreground">
            {hit.score.toFixed(3)}
          </span>
        </span>
      </div>
      <p className="whitespace-pre-wrap text-[13px] leading-6">
        {expanded ? hit.text : truncated}
      </p>
      {hit.tags.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {hit.tags.map((t) => (
            <Badge key={t} variant="outline" className="text-[10px]">
              {t}
            </Badge>
          ))}
        </div>
      )}
      {canExpand && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="mt-2 text-[11px] text-muted-foreground underline underline-offset-2 hover:text-foreground"
        >
          {expanded ? "Show less" : "Show more"}
        </button>
      )}
    </div>
  );
}

function basename(p: string): string {
  const parts = p.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || p;
}
