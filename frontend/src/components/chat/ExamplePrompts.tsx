"use client";

import {
  Clock,
  Package,
  PieChart,
  Sparkles,
  TrendingUp,
  Wallet,
} from "lucide-react";

const PROMPTS: Array<{ label: string; icon: React.ReactNode; prompt: string }> = [
  {
    label: "Salary expenses by role",
    icon: <Wallet className="size-4 text-[--color-chart-1]" />,
    prompt:
      "Current salary expenses by role — see where salary costs are concentrated",
  },
  {
    label: "Hiring trends over time",
    icon: <TrendingUp className="size-4 text-[--color-chart-2]" />,
    prompt: "Hiring trends over time",
  },
  {
    label: "Revenue by category (enterprise)",
    icon: <PieChart className="size-4 text-[--color-chart-3]" />,
    prompt: "Revenue by category for enterprise customers only",
  },
  {
    label: "US orders delivered last month",
    icon: <Package className="size-4 text-[--color-chart-4]" />,
    prompt: "How many orders from the US were delivered last month?",
  },
  {
    label: "Average employee tenure",
    icon: <Clock className="size-4 text-[--color-chart-5]" />,
    prompt: "What's the average tenure of our employees?",
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
