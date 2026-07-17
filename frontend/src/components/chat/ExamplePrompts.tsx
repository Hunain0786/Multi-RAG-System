"use client";

import {
  BarChart3,
  BookOpen,
  Brain,
  Layers,
  Sparkles,
} from "lucide-react";

const PROMPTS: Array<{ label: string; icon: React.ReactNode; prompt: string }> = [
  {
    label: "Top 5 products by revenue this quarter",
    icon: <BarChart3 className="size-4 text-[--color-chart-1]" />,
    prompt:
      "What are the top 5 products by revenue this quarter, grouped by product category?",
  },
  {
    label: "What's our return policy?",
    icon: <BookOpen className="size-4 text-[--color-chart-2]" />,
    prompt:
      "What is our return policy? Cite the specific timeframes and conditions from the policy doc.",
  },
  {
    label: "Refund rate + policy for electronics",
    icon: <Layers className="size-4 text-[--color-chart-3]" />,
    prompt:
      "How many refunds did we process in the last 90 days, and what does our policy say about electronics refunds?",
  },
  {
    label: "Remember a preference",
    icon: <Brain className="size-4 text-[--color-chart-4]" />,
    prompt:
      "Remember that I always want revenue reports in USD and grouped by month.",
  },
];

interface ExamplePromptsProps {
  onPick: (prompt: string) => void;
}

export function ExamplePrompts({ onPick }: ExamplePromptsProps) {
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col items-center gap-6 px-6 py-10">
      <div className="flex flex-col items-center gap-2 text-center">
        <div className="rounded-full border bg-card p-3">
          <Sparkles className="size-6 text-primary" />
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Ask the multi-rag agent
        </h1>
        <p className="max-w-md text-sm text-muted-foreground">
          One prompt, three backends: a Postgres semantic layer, a Pinecone
          document index, and a read-only SQL escape hatch. Tool calls stream
          inline so you can see exactly what the agent did.
        </p>
      </div>

      <div className="grid w-full grid-cols-1 gap-2 sm:grid-cols-2">
        {PROMPTS.map((p) => (
          <button
            key={p.label}
            type="button"
            onClick={() => onPick(p.prompt)}
            className="flex items-start gap-3 rounded-lg border bg-card p-3 text-left text-sm transition-colors hover:bg-accent/50"
          >
            <span className="mt-0.5">{p.icon}</span>
            <span className="text-foreground/90">{p.label}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
