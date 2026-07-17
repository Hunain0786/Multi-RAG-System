"use client";

import { useCallback, useEffect, useState } from "react";
import { Brain, Loader2, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { deleteMemoryFact, listMemoryFacts } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { FactKind, MemoryFactSummary } from "@/lib/types";

const KIND_COLORS: Record<FactKind, string> = {
  preference: "bg-[--color-chart-1]/15 text-[--color-chart-1]",
  fact: "bg-[--color-chart-2]/15 text-[--color-chart-2]",
  constraint: "bg-[--color-chart-3]/15 text-[--color-chart-3]",
};

export function MemoryTable() {
  const [facts, setFacts] = useState<MemoryFactSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<FactKind | "all">("all");
  const [toDelete, setToDelete] = useState<MemoryFactSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await listMemoryFacts();
      setFacts(res.facts);
    } catch (e) {
      toast.error(`Failed to load memory: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching, load() sets state on completion
    void load();
  }, [load]);

  const visible =
    filter === "all" ? facts : facts.filter((f) => f.kind === filter);

  const doDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteMemoryFact(toDelete.id);
      toast.success("Memory forgotten");
      setToDelete(null);
      await load();
    } catch (e) {
      toast.error(`Delete failed: ${(e as Error).message}`);
    } finally {
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm text-muted-foreground">
          {loading
            ? "Loading…"
            : `${visible.length} of ${facts.length} memor${
                facts.length === 1 ? "y" : "ies"
              }`}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Filter
          </span>
          <Select
            value={filter}
            onValueChange={(v) => setFilter(v as FactKind | "all")}
          >
            <SelectTrigger className="h-8 w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="preference">preference</SelectItem>
              <SelectItem value="fact">fact</SelectItem>
              <SelectItem value="constraint">constraint</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table className="text-[13px]">
          <TableHeader>
            <TableRow className="bg-muted/40">
              <TableHead>Fact</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead>Remembered</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && visible.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="py-10 text-center text-muted-foreground"
                >
                  <Loader2 className="mx-auto size-4 animate-spin" />
                </TableCell>
              </TableRow>
            )}
            {!loading && visible.length === 0 && (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="py-10 text-center text-sm text-muted-foreground"
                >
                  <Brain className="mx-auto mb-2 size-5" />
                  Nothing remembered yet. Ask the agent to remember something,
                  e.g. &ldquo;Remember I prefer amounts in INR&rdquo;.
                </TableCell>
              </TableRow>
            )}
            {visible.map((f) => (
              <TableRow key={f.id}>
                <TableCell className="max-w-[36rem] whitespace-normal">
                  {f.text}
                </TableCell>
                <TableCell>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${KIND_COLORS[f.kind]}`}
                  >
                    {f.kind}
                  </span>
                </TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">
                  {formatDateTime(f.created_at)}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-destructive"
                    onClick={() => setToDelete(f)}
                    aria-label="Forget this memory"
                  >
                    <Trash2 className="size-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <Dialog
        open={toDelete !== null}
        onOpenChange={(open) => !open && setToDelete(null)}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Forget this memory?</DialogTitle>
            <DialogDescription>
              {toDelete
                ? `The agent will no longer see "${truncate(toDelete.text, 80)}" in future turns.`
                : ""}{" "}
              The row stays in Postgres for audit but its vector is dropped from
              Pinecone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="ghost"
              onClick={() => setToDelete(null)}
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={doDelete}
              disabled={deleting}
              className="gap-2"
            >
              {deleting && <Loader2 className="size-4 animate-spin" />}
              Forget
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function truncate(s: string, n: number): string {
  return s.length > n ? `${s.slice(0, n - 1)}…` : s;
}
