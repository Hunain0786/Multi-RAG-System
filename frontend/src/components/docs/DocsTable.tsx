"use client";

import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Loader2, Trash2 } from "lucide-react";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { deleteDoc, listDocs } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import type { DocSummary, DocType } from "@/lib/types";

const DOC_TYPE_COLORS: Record<DocType, string> = {
  policy: "bg-[--color-chart-1]/15 text-[--color-chart-1]",
  manual: "bg-[--color-chart-2]/15 text-[--color-chart-2]",
  faq: "bg-[--color-chart-3]/15 text-[--color-chart-3]",
  other: "bg-muted text-muted-foreground",
};

interface DocsTableProps {
  refreshKey: number;
}

export function DocsTable({ refreshKey }: DocsTableProps) {
  const [docs, setDocs] = useState<DocSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState<DocType | "all">("all");
  const [toDelete, setToDelete] = useState<DocSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useMemo(
    () => async () => {
      setLoading(true);
      try {
        const res = await listDocs(filter === "all" ? undefined : filter);
        setDocs(res.docs);
      } catch (e) {
        toast.error(`Failed to load: ${(e as Error).message}`);
      } finally {
        setLoading(false);
      }
    },
    [filter],
  );

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- data fetching, load() sets state on completion
    void load();
  }, [load, refreshKey]);

  const doDelete = async () => {
    if (!toDelete) return;
    setDeleting(true);
    try {
      await deleteDoc(toDelete.id);
      toast.success(`Deleted ${basename(toDelete.source_path)}`);
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
          {loading ? "Loading…" : `${docs.length} document${docs.length === 1 ? "" : "s"}`}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Filter
          </span>
          <Select
            value={filter}
            onValueChange={(v) => setFilter(v as DocType | "all")}
          >
            <SelectTrigger className="h-8 w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All</SelectItem>
              <SelectItem value="policy">policy</SelectItem>
              <SelectItem value="manual">manual</SelectItem>
              <SelectItem value="faq">faq</SelectItem>
              <SelectItem value="other">other</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-md border">
        <Table className="text-[13px]">
          <TableHeader>
            <TableRow className="bg-muted/40">
              <TableHead>Source</TableHead>
              <TableHead>Type</TableHead>
              <TableHead className="text-right">Chunks</TableHead>
              <TableHead className="text-right">Tokens</TableHead>
              <TableHead>Ingested</TableHead>
              <TableHead className="w-10" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && docs.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-muted-foreground">
                  <Loader2 className="mx-auto size-4 animate-spin" />
                </TableCell>
              </TableRow>
            )}
            {!loading && docs.length === 0 && (
              <TableRow>
                <TableCell colSpan={6} className="py-10 text-center text-sm text-muted-foreground">
                  No documents ingested yet. Upload one above.
                </TableCell>
              </TableRow>
            )}
            {docs.map((d) => (
              <TableRow key={d.id}>
                <TableCell className="max-w-[26rem] truncate font-mono">
                  {basename(d.source_path)}
                </TableCell>
                <TableCell>
                  <span
                    className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${DOC_TYPE_COLORS[d.doc_type]}`}
                  >
                    {d.doc_type}
                  </span>
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {d.chunk_count}
                </TableCell>
                <TableCell className="text-right tabular-nums">
                  {d.tokens.toLocaleString()}
                </TableCell>
                <TableCell className="whitespace-nowrap text-muted-foreground">
                  {formatDateTime(d.ingested_at)}
                </TableCell>
                <TableCell>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-8 text-muted-foreground hover:text-destructive"
                    onClick={() => setToDelete(d)}
                    aria-label={`Delete ${d.source_path}`}
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
            <DialogTitle>Delete document?</DialogTitle>
            <DialogDescription>
              This removes{" "}
              <span className="font-mono">
                {toDelete ? basename(toDelete.source_path) : ""}
              </span>{" "}
              from Postgres and drops its vectors from Pinecone. This cannot be
              undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setToDelete(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={doDelete}
              disabled={deleting}
              className="gap-2"
            >
              {deleting && <Loader2 className="size-4 animate-spin" />}
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

function basename(p: string): string {
  const parts = p.replace(/\\/g, "/").split("/");
  return parts[parts.length - 1] || p;
}
