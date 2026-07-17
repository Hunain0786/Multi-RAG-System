"use client";

import { Brain, Check, Search, Trash2 } from "lucide-react";

import type {
  FactKind,
  ForgetResult,
  RecallResult,
  RememberResult,
} from "@/lib/types";

const KIND_STYLES: Record<FactKind, string> = {
  preference: "bg-[--color-chart-1]/15 text-[--color-chart-1]",
  fact: "bg-[--color-chart-2]/15 text-[--color-chart-2]",
  constraint: "bg-[--color-chart-3]/15 text-[--color-chart-3]",
};

function KindPill({ kind }: { kind: FactKind }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide ${KIND_STYLES[kind]}`}
    >
      {kind}
    </span>
  );
}

export function RememberCard({ data }: { data: RememberResult }) {
  return (
    <div className="flex items-start gap-3 rounded-md border bg-background px-3 py-2 text-[13px]">
      <div className="mt-0.5 rounded-full bg-emerald-500/15 p-1.5 text-emerald-600">
        <Brain className="size-4" />
      </div>
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2">
          <span className="font-medium">Remembered</span>
          <KindPill kind={data.kind} />
        </div>
        <div className="text-foreground">{data.text}</div>
        <div className="font-mono text-[10px] text-muted-foreground">
          id {data.id}
        </div>
      </div>
    </div>
  );
}

export function RecallCard({ data }: { data: RecallResult }) {
  if (data.hits.length === 0) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-dashed bg-muted/20 px-3 py-2 text-[12px] text-muted-foreground">
        <Search className="size-3.5" />
        No memories match &ldquo;{data.query}&rdquo;.
      </div>
    );
  }
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
        <Search className="size-3.5" />
        Memories matching{" "}
        <span className="rounded bg-muted px-1.5 py-0.5 font-mono">
          {data.query}
        </span>
      </div>
      <ul className="space-y-1.5">
        {data.hits.map((h) => (
          <li
            key={h.id}
            className="flex items-start gap-2 rounded-md border bg-background px-3 py-2 text-[13px]"
          >
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <KindPill kind={h.kind} />
                <span className="text-[11px] tabular-nums text-muted-foreground">
                  score {h.similarity.toFixed(3)}
                </span>
              </div>
              <div className="mt-1">{h.text}</div>
              <div className="mt-0.5 font-mono text-[10px] text-muted-foreground">
                id {h.id}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ForgetCard({ data }: { data: ForgetResult }) {
  const ok = data.deleted;
  const Icon = ok ? Trash2 : Check;
  return (
    <div className="flex items-start gap-3 rounded-md border bg-background px-3 py-2 text-[13px]">
      <div
        className={`mt-0.5 rounded-full p-1.5 ${
          ok
            ? "bg-rose-500/15 text-rose-600"
            : "bg-muted text-muted-foreground"
        }`}
      >
        <Icon className="size-4" />
      </div>
      <div className="flex-1 space-y-1">
        <div className="font-medium">
          {ok ? "Forgot memory" : "Nothing to forget"}
        </div>
        <div className="font-mono text-[11px] text-muted-foreground">
          id {data.id}
          {data.reason ? ` — ${data.reason}` : null}
        </div>
      </div>
    </div>
  );
}
