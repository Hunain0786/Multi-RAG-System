"use client";

import { useCallback, useRef, useState } from "react";
import { FileUp, Loader2, Tag, X } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ingestDoc } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { DocType } from "@/lib/types";

const ACCEPTED = ".pdf,.txt,.md,application/pdf,text/plain,text/markdown";
const ACCEPTED_EXTS = new Set([".pdf", ".txt", ".md"]);

const DOC_TYPES: DocType[] = ["policy", "manual", "faq", "other"];

interface DocUploadProps {
  onIngested: () => void;
}

export function DocUpload({ onIngested }: DocUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragging, setDragging] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocType | "auto">("auto");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [phase, setPhase] = useState<"idle" | "uploading" | "processing">("idle");

  const pickFile = useCallback((f: File | null) => {
    if (!f) return;
    const ext = `.${f.name.split(".").pop()?.toLowerCase() ?? ""}`;
    if (!ACCEPTED_EXTS.has(ext)) {
      toast.error("Unsupported file. Use .pdf, .txt, or .md");
      return;
    }
    setFile(f);
  }, []);

  const addTag = useCallback((raw: string) => {
    const next = raw
      .split(",")
      .map((t) => t.trim().toLowerCase())
      .filter(Boolean);
    if (next.length === 0) return;
    setTags((prev) => {
      const merged = [...prev];
      for (const t of next) {
        if (!merged.includes(t) && merged.length < 12) merged.push(t);
      }
      return merged;
    });
    setTagInput("");
  }, []);

  const removeTag = (t: string) => {
    setTags((prev) => prev.filter((x) => x !== t));
  };

  const reset = () => {
    setFile(null);
    setProgress(0);
    setPhase("idle");
    setUploading(false);
    if (inputRef.current) inputRef.current.value = "";
  };

  const submit = async () => {
    if (!file || uploading) return;
    setUploading(true);
    setPhase("uploading");
    setProgress(0);
    try {
      const res = await ingestDoc({
        file,
        docType: docType === "auto" ? undefined : docType,
        tags,
        onProgress: (pct) => {
          setProgress(pct);
          if (pct >= 100) setPhase("processing");
        },
      });
      if (res.reused) {
        toast.message("Already indexed", {
          description: "Identical content already exists — skipped re-embedding.",
        });
      } else {
        toast.success(`Ingested ${file.name}`, {
          description: `${res.chunks_added} chunks · ${res.tokens.toLocaleString()} tokens`,
        });
      }
      reset();
      onIngested();
    } catch (e) {
      if ((e as Error).name === "AbortError") return;
      toast.error(`Upload failed: ${(e as Error).message}`);
      setPhase("idle");
      setUploading(false);
      setProgress(0);
    }
  };

  return (
    <div className="space-y-4 rounded-md border bg-muted/10 p-4">
      <div
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        onDragEnter={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(true);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(true);
        }}
        onDragLeave={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(false);
        }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          setDragging(false);
          const f = e.dataTransfer.files?.[0] ?? null;
          pickFile(f);
        }}
        onClick={() => inputRef.current?.click()}
        className={cn(
          "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-md border border-dashed px-4 py-10 text-center transition-colors",
          dragging
            ? "border-primary bg-primary/5"
            : "border-muted-foreground/25 hover:border-muted-foreground/50 hover:bg-muted/30",
          uploading && "pointer-events-none opacity-60",
        )}
      >
        <div className="rounded-full bg-muted p-2.5 text-muted-foreground">
          <FileUp className="size-5" />
        </div>
        <div className="space-y-1">
          <p className="text-sm font-medium">
            {file ? file.name : "Drop a document here"}
          </p>
          <p className="text-xs text-muted-foreground">
            {file
              ? `${(file.size / 1024).toFixed(1)} KB · click to change`
              : "Text PDF, TXT, or Markdown — scanned/image PDFs won’t work"}
          </p>
        </div>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED}
          className="hidden"
          disabled={uploading}
          onChange={(e) => pickFile(e.target.files?.[0] ?? null)}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-[10rem_1fr]">
        <div className="space-y-1.5">
          <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Type
          </label>
          <Select
            value={docType}
            onValueChange={(v) => setDocType(v as DocType | "auto")}
            disabled={uploading}
          >
            <SelectTrigger className="h-8 w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="auto">auto-detect</SelectItem>
              {DOC_TYPES.map((t) => (
                <SelectItem key={t} value={t}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1.5">
          <label className="text-[11px] uppercase tracking-wide text-muted-foreground">
            Tags
          </label>
          <div className="flex min-h-8 flex-wrap items-center gap-1.5 rounded-md border bg-background px-2 py-1">
            <Tag className="size-3.5 shrink-0 text-muted-foreground" />
            {tags.map((t) => (
              <button
                key={t}
                type="button"
                disabled={uploading}
                onClick={() => removeTag(t)}
                className="inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5 text-[11px] font-medium hover:bg-muted/80"
              >
                {t}
                <X className="size-3 opacity-60" />
              </button>
            ))}
            <input
              value={tagInput}
              disabled={uploading}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === ",") {
                  e.preventDefault();
                  addTag(tagInput);
                } else if (e.key === "Backspace" && !tagInput && tags.length) {
                  removeTag(tags[tags.length - 1]);
                }
              }}
              onBlur={() => addTag(tagInput)}
              placeholder={tags.length ? "" : "returns, shipping…"}
              className="min-w-[7rem] flex-1 bg-transparent py-0.5 text-sm outline-none placeholder:text-muted-foreground/60"
            />
          </div>
        </div>
      </div>

      {(uploading || progress > 0) && (
        <div className="space-y-1.5">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span>
              {phase === "processing"
                ? "Embedding & indexing…"
                : phase === "uploading"
                  ? "Uploading…"
                  : "Ready"}
            </span>
            <span className="tabular-nums">
              {phase === "processing" ? "…" : `${progress}%`}
            </span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-muted">
            <div
              className={cn(
                "h-full rounded-full bg-primary transition-[width] duration-200",
                phase === "processing" && "animate-pulse",
              )}
              style={{
                width: phase === "processing" ? "100%" : `${progress}%`,
              }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        {file && !uploading && (
          <Button type="button" variant="ghost" size="sm" onClick={reset}>
            Clear
          </Button>
        )}
        <Button
          type="button"
          size="sm"
          disabled={!file || uploading}
          onClick={() => void submit()}
          className="gap-1.5"
        >
          {uploading && <Loader2 className="size-3.5 animate-spin" />}
          {uploading
            ? phase === "processing"
              ? "Indexing…"
              : "Uploading…"
            : "Ingest document"}
        </Button>
      </div>
    </div>
  );
}
