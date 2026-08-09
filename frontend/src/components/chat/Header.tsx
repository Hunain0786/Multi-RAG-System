"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  Brain,
  ChevronDown,
  Database,
  FileText,
  History,
  Loader2,
  PlusCircle,
  Trash2,
} from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { deleteConversation, getHealth, listConversations } from "@/lib/api";
import { useConversation } from "@/store/conversation";
import type { ConversationSummary, HealthResponse } from "@/lib/types";

interface HeaderProps {
  showChatLink?: boolean;
  showNewChat?: boolean;
}

export function Header({
  showChatLink = false,
  showNewChat = true,
}: HeaderProps) {
  const reset = useConversation((s) => s.reset);
  const loadConversation = useConversation((s) => s.loadConversation);
  const activeConversationId = useConversation((s) => s.conversationId);

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [convsLoading, setConvsLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;
    async function poll() {
      try {
        const h = await getHealth();
        if (!cancelled) setHealth(h);
      } catch {
        if (!cancelled)
          setHealth({
            status: "degraded",
            postgres: false,
            pinecone: false,
            pinecone_stats: {},
          });
      }
    }
    void poll();
    const id = window.setInterval(poll, 15_000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, []);

  const loadConversations = useCallback(async () => {
    setConvsLoading(true);
    try {
      const res = await listConversations();
      setConversations(res.conversations);
    } catch {
      setConversations([]);
    } finally {
      setConvsLoading(false);
    }
  }, []);

  const handleDeleteConversation = async (id: string) => {
    try {
      await deleteConversation(id);
      toast.success("Conversation deleted");
      if (id === activeConversationId) reset();
      await loadConversations();
    } catch (e) {
      toast.error(`Delete failed: ${(e as Error).message}`);
    }
  };

  const color =
    health === null
      ? "bg-muted-foreground"
      : health.status === "ok"
        ? "bg-emerald-500"
        : health.postgres || health.pinecone
          ? "bg-amber-500"
          : "bg-rose-500";
  const label =
    health === null
      ? "checking backend..."
      : `postgres ${health.postgres ? "ok" : "down"} · pinecone ${health.pinecone ? "ok" : "down"}`;

  return (
    <header className="sticky top-0 z-10 border-b bg-background/80 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-4">
        <Link href="/" className="flex items-center gap-2 font-semibold">
          <Database className="size-5 text-primary" />
          <span>multi-rag</span>
          <span className="rounded bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
            agent
          </span>
        </Link>

        <div className="flex items-center gap-2">
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
                <span className={`inline-block size-2 rounded-full ${color}`} />
                <span className="hidden sm:inline">
                  {health?.status ?? "…"}
                </span>
              </div>
            </TooltipTrigger>
            <TooltipContent side="bottom">{label}</TooltipContent>
          </Tooltip>

          <DropdownMenu
            onOpenChange={(open) => {
              if (open) void loadConversations();
            }}
          >
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-1.5">
                <History className="size-4" />
                <span className="hidden sm:inline">Conversations</span>
                <ChevronDown className="size-3.5 opacity-60" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel className="flex items-center justify-between">
                <span>Recent</span>
                {convsLoading && (
                  <Loader2 className="size-3.5 animate-spin text-muted-foreground" />
                )}
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              {conversations.length === 0 && !convsLoading && (
                <div className="px-2 py-4 text-center text-xs text-muted-foreground">
                  No prior conversations.
                </div>
              )}
              {conversations.slice(0, 20).map((c) => (
                <DropdownMenuItem
                  key={c.id}
                  onSelect={() => void loadConversation(c.id)}
                  className="flex items-start gap-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-sm">
                      {c.title ?? "(untitled)"}
                    </div>
                    <div className="text-[10px] text-muted-foreground">
                      {c.message_count} msg
                      {c.message_count === 1 ? "" : "s"} ·{" "}
                      {new Date(c.updated_at).toLocaleString()}
                    </div>
                  </div>
                  {c.id === activeConversationId && (
                    <span className="mt-0.5 rounded bg-emerald-500/15 px-1.5 py-0.5 text-[9px] font-medium uppercase tracking-wide text-emerald-600">
                      current
                    </span>
                  )}
                  <button
                    type="button"
                    aria-label="Delete conversation"
                    className="ml-1 rounded p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      void handleDeleteConversation(c.id);
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          <Button asChild variant="ghost" size="sm">
            <Link href="/chat" className="gap-1.5">
              Chat
            </Link>
          </Button>

          <Button asChild variant="ghost" size="sm">
            <Link href="/docs" className="gap-1.5">
              <FileText className="size-4" />
              <span className="hidden sm:inline">Docs</span>
            </Link>
          </Button>

          <Button asChild variant="ghost" size="sm">
            <Link href="/live-updates" className="gap-1.5">
              <Activity className="size-4" />
              <span className="hidden sm:inline">Live Updates</span>
            </Link>
          </Button>

          <Button asChild variant="ghost" size="sm">
            <Link href="/memory" className="gap-1.5">
              <Brain className="size-4" />
              <span className="hidden sm:inline">Memory</span>
            </Link>
          </Button>

          {showChatLink && (
            <Button asChild variant="outline" size="sm">
              <Link href="/" className="gap-1.5">
                Home
              </Link>
            </Button>
          )}
          {showNewChat && (
            <Button
              variant="outline"
              size="sm"
              onClick={reset}
              className="gap-1.5"
            >
              <PlusCircle className="size-4" />
              New chat
            </Button>
          )}
        </div>
      </div>
    </header>
  );
}
