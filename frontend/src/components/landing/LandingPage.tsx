import Link from "next/link";
import {
  ArrowRight,
  Brain,
  Database,
  FileText,
  Layers,
  ShieldCheck,
  Sparkles,
  Workflow,
} from "lucide-react";

import { Button } from "@/components/ui/button";

const FEATURES = [
  {
    icon: Database,
    title: "Governed SQL metrics",
    body: "Ask about sales, inventory, finance, and HR through a curated semantic layer — not free-form SQL guessing.",
  },
  {
    icon: FileText,
    title: "Document RAG",
    body: "Search policies, FAQs, and manuals in Pinecone with citations, so every policy claim points back to a chunk.",
  },
  {
    icon: Brain,
    title: "Durable agent memory",
    body: "Remember preferences and facts across conversations, then recall or forget them when the context changes.",
  },
  {
    icon: Workflow,
    title: "Tool-use agent loop",
    body: "Anthropic tool_use streams SQL tables, charts, and doc hits in one answer — with live progress you can audit.",
  },
] as const;

const BENEFITS = [
  {
    icon: ShieldCheck,
    title: "Answers you can trust",
    body: "Metrics are compiled from a registry. Documents are cited. Raw SQL stays a guarded escape hatch.",
  },
  {
    icon: Layers,
    title: "One place for ops questions",
    body: "Hybrid prompts span warehouse numbers and return policy in a single turn — no tab-hopping between tools.",
  },
  {
    icon: Sparkles,
    title: "Built for demos and daily ops",
    body: "Upload corpora, inspect memory, watch live KPI insights, and chat with charts beside the transcript.",
  },
] as const;

export function LandingPage() {
  return (
    <div className="landing min-h-screen bg-background text-foreground">
      <LandingNav />

      {/* Hero — one composition: brand, headline, sentence, CTAs, full-bleed visual */}
      <section className="relative isolate min-h-[100svh] overflow-hidden">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 landing-hero-bg"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute inset-0 landing-hero-grain opacity-[0.35]"
        />
        <HeroStage />

        <div className="relative z-10 mx-auto flex min-h-[100svh] max-w-6xl flex-col justify-center px-4 pb-16 pt-28 sm:pb-20 sm:pt-32">
          <div className="relative max-w-xl">
            <div
              aria-hidden
              className="pointer-events-none absolute -inset-x-4 -inset-y-8 -z-10 bg-gradient-to-r from-background via-background/92 to-transparent sm:-inset-x-6"
            />
            <div className="space-y-6 landing-fade-up">
              <p className="font-[family-name:var(--font-display)] text-4xl font-semibold tracking-tight text-primary sm:text-5xl md:text-6xl">
                multi-rag
              </p>
              <h1 className="font-[family-name:var(--font-display)] text-2xl font-medium leading-snug tracking-tight text-foreground sm:text-3xl md:text-[2.15rem] md:leading-[1.25]">
                One agent. Structured data, documents, and memory — answered together.
              </h1>
              <p className="max-w-md text-base leading-relaxed text-muted-foreground sm:text-lg">
                An ops copilot that compiles governed metrics, retrieves cited
                policies, and keeps context across chats.
              </p>
              <div className="flex flex-wrap items-center gap-3 pt-1">
                <Button asChild size="lg" className="gap-2 px-4">
                  <Link href="/chat">
                    Open the agent
                    <ArrowRight className="size-4" />
                  </Link>
                </Button>
                <Button asChild variant="outline" size="lg" className="px-4">
                  <Link href="/docs">Browse documents</Link>
                </Button>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features — one purpose */}
      <section className="border-t border-border/70 bg-card/40">
        <div className="mx-auto max-w-6xl px-4 py-20 sm:py-24">
          <div className="max-w-2xl space-y-3 landing-fade-up">
            <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight sm:text-3xl">
              What it brings together
            </h2>
            <p className="text-muted-foreground">
              Three retrieval surfaces, one streaming tool-use loop — built for
              e-commerce operations questions that span systems.
            </p>
          </div>

          <ul className="mt-12 grid gap-10 sm:grid-cols-2">
            {FEATURES.map((f, i) => (
              <li
                key={f.title}
                className="landing-fade-up space-y-3 border-t border-border pt-6"
                style={{ animationDelay: `${120 + i * 80}ms` }}
              >
                <div className="flex items-center gap-2.5 text-primary">
                  <f.icon className="size-5 shrink-0" strokeWidth={1.75} />
                  <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-foreground">
                    {f.title}
                  </h3>
                </div>
                <p className="max-w-md text-sm leading-relaxed text-muted-foreground sm:text-[15px]">
                  {f.body}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Benefits — one purpose */}
      <section className="relative overflow-hidden border-t border-border/70">
        <div
          aria-hidden
          className="pointer-events-none absolute inset-y-0 right-0 w-1/2 bg-[radial-gradient(ellipse_at_right,oklch(0.90_0.035_78/_0.7),transparent_65%)]"
        />
        <div className="relative mx-auto max-w-6xl px-4 py-20 sm:py-24">
          <div className="max-w-2xl space-y-3">
            <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight sm:text-3xl">
              Why teams use it
            </h2>
            <p className="text-muted-foreground">
              Less context-switching, fewer hallucinated numbers, and a clear
              trail from question to evidence.
            </p>
          </div>

          <ul className="mt-14 space-y-12 md:space-y-14">
            {BENEFITS.map((b, i) => (
              <li
                key={b.title}
                className="landing-fade-up grid gap-3 md:grid-cols-[minmax(0,14rem)_1fr] md:gap-10"
                style={{ animationDelay: `${100 + i * 90}ms` }}
              >
                <div className="flex items-start gap-2.5 text-primary">
                  <b.icon className="mt-0.5 size-5 shrink-0" strokeWidth={1.75} />
                  <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold tracking-tight text-foreground">
                    {b.title}
                  </h3>
                </div>
                <p className="max-w-xl text-sm leading-relaxed text-muted-foreground sm:text-[15px] md:pt-0.5">
                  {b.body}
                </p>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Closing CTA */}
      <section className="border-t border-border/70 bg-muted/40">
        <div className="mx-auto flex max-w-6xl flex-col items-start gap-6 px-4 py-16 sm:flex-row sm:items-center sm:justify-between sm:py-20">
          <div className="max-w-lg space-y-2">
            <h2 className="font-[family-name:var(--font-display)] text-2xl font-semibold tracking-tight">
              Ask the warehouse and the policy in one breath.
            </h2>
            <p className="text-sm text-muted-foreground sm:text-base">
              Start a chat, or ingest a document and watch retrieval light up.
            </p>
          </div>
          <Button asChild size="lg" className="gap-2 shrink-0 px-4">
            <Link href="/chat">
              Start chatting
              <ArrowRight className="size-4" />
            </Link>
          </Button>
        </div>
      </section>

      <footer className="border-t border-border/60">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-6 text-xs text-muted-foreground">
          <span className="font-[family-name:var(--font-display)] font-medium text-foreground/80">
            multi-rag
          </span>
          <span>SQL · Pinecone · Anthropic tool_use</span>
        </div>
      </footer>
    </div>
  );
}

function LandingNav() {
  return (
    <header className="absolute inset-x-0 top-0 z-20">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link
          href="/"
          className="flex items-center gap-2 font-[family-name:var(--font-display)] text-sm font-semibold tracking-tight"
        >
          <Database className="size-4 text-primary" />
          multi-rag
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link href="/docs">Docs</Link>
          </Button>
          <Button asChild variant="ghost" size="sm" className="hidden sm:inline-flex">
            <Link href="/live-updates">Live Updates</Link>
          </Button>
          <Button asChild size="sm" className="gap-1.5">
            <Link href="/chat">
              Open chat
              <ArrowRight className="size-3.5" />
            </Link>
          </Button>
        </nav>
      </div>
    </header>
  );
}

/** Full-bleed product stage — three retrieval streams converging (no floating chips). */
function HeroStage() {
  return (
    <div
      aria-hidden
      className="pointer-events-none absolute inset-0 z-0 overflow-hidden opacity-90"
    >
      <svg
        className="absolute inset-0 h-full w-full text-primary"
        viewBox="0 0 1440 900"
        fill="none"
        preserveAspectRatio="xMidYMid slice"
      >
        <defs>
          <linearGradient id="stream" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.22" />
            <stop offset="55%" stopColor="currentColor" stopOpacity="0.1" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.02" />
          </linearGradient>
          <radialGradient id="well" cx="72%" cy="58%" r="35%">
            <stop offset="0%" stopColor="oklch(0.90 0.035 78)" stopOpacity="0.85" />
            <stop offset="100%" stopColor="oklch(0.90 0.035 78)" stopOpacity="0" />
          </radialGradient>
        </defs>

        <rect width="1440" height="900" fill="url(#well)" />

        {/* Postgres stream */}
        <path
          className="landing-draw"
          d="M-40 180 C280 160, 520 280, 980 420"
          stroke="url(#stream)"
          strokeWidth="2.5"
        />
        {/* Docs stream */}
        <path
          className="landing-draw"
          style={{ animationDelay: "0.35s" }}
          d="M1520 140 C1180 220, 1080 320, 980 420"
          stroke="url(#stream)"
          strokeWidth="2.5"
        />
        {/* Memory stream */}
        <path
          className="landing-draw"
          style={{ animationDelay: "0.7s" }}
          d="M-20 620 C360 540, 640 480, 980 420"
          stroke="url(#stream)"
          strokeWidth="2.5"
        />

        {/* Convergence node */}
        <circle
          className="landing-pulse-node"
          cx="980"
          cy="420"
          r="10"
          fill="currentColor"
          fillOpacity="0.35"
        />
        <circle cx="980" cy="420" r="3.5" fill="currentColor" fillOpacity="0.7" />

        {/* Soft answer ribbon extending from the node */}
        <path
          className="landing-draw"
          style={{ animationDelay: "1s" }}
          d="M990 420 C1120 430, 1240 470, 1480 560"
          stroke="currentColor"
          strokeOpacity="0.18"
          strokeWidth="1.5"
          strokeDasharray="6 10"
        />

        {/* Source labels integrated into the plane (not floating badges) */}
        <text
          x="72"
          y="168"
          className="landing-stream-label fill-primary/45"
          style={{ fontSize: 13, letterSpacing: "0.08em" }}
        >
          POSTGRES METRICS
        </text>
        <text
          x="1180"
          y="128"
          className="landing-stream-label fill-primary/45"
          style={{ fontSize: 13, letterSpacing: "0.08em" }}
        >
          PINECONE DOCS
        </text>
        <text
          x="72"
          y="650"
          className="landing-stream-label fill-primary/45"
          style={{ fontSize: 13, letterSpacing: "0.08em" }}
        >
          AGENT MEMORY
        </text>
      </svg>
    </div>
  );
}
