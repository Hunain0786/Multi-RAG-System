import type {
  ConversationListResponse,
  ConversationMemoryResponse,
  ConversationMessagesResponse,
  DocListResponse,
  DocType,
  HealthResponse,
  IngestResponse,
  InsightsResponse,
  MemoryFactListResponse,
} from "@/lib/types";

/**
 * Browser-side client for the Next.js API routes (same origin, no CORS).
 * The Next.js routes proxy through to the FastAPI backend so `BACKEND_URL`
 * is never exposed to the browser.
 */

async function unwrap<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(
      body ? `${res.status} ${res.statusText}: ${body}` : `${res.status} ${res.statusText}`,
    );
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

function parseErrorBody(body: string, status: number, statusText: string): Error {
  if (!body) return new Error(`${status} ${statusText}`);
  try {
    const json = JSON.parse(body) as { detail?: unknown };
    if (typeof json.detail === "string") return new Error(json.detail);
    if (Array.isArray(json.detail)) {
      const msgs = json.detail
        .map((d) => {
          if (d && typeof d === "object" && "msg" in d) {
            return String((d as { msg: unknown }).msg);
          }
          return null;
        })
        .filter(Boolean);
      if (msgs.length) return new Error(msgs.join("; "));
    }
  } catch {
    // not JSON — fall through
  }
  return new Error(`${status} ${statusText}: ${body}`);
}

// ---------------------------------------------------------------------------
// Docs (list / delete / ingest)
// ---------------------------------------------------------------------------

export async function listDocs(docType?: DocType): Promise<DocListResponse> {
  const qs = docType ? `?doc_type=${encodeURIComponent(docType)}` : "";
  return unwrap(await fetch(`/api/docs${qs}`, { cache: "no-store" }));
}

export async function deleteDoc(id: string): Promise<void> {
  await unwrap<void>(
    await fetch(`/api/docs/${encodeURIComponent(id)}`, { method: "DELETE" }),
  );
}

export interface IngestDocOptions {
  file: File;
  docType?: DocType;
  tags?: string[];
  /** 0–100 while bytes are uploading; may stay at 100 during server-side ingest. */
  onProgress?: (pct: number) => void;
  signal?: AbortSignal;
}

/**
 * Multipart upload with XHR so we can report upload progress. After the
 * request body finishes, the server still embeds + upserts — UI should treat
 * 100% as "processing" until this promise resolves.
 */
export function ingestDoc(opts: IngestDocOptions): Promise<IngestResponse> {
  const { file, docType, tags, onProgress, signal } = opts;
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/docs");
    xhr.responseType = "text";

    const onAbort = () => {
      xhr.abort();
      reject(new DOMException("Upload aborted", "AbortError"));
    };
    signal?.addEventListener("abort", onAbort);

    xhr.upload.onprogress = (e) => {
      if (!e.lengthComputable || !onProgress) return;
      onProgress(Math.min(99, Math.round((e.loaded / e.total) * 100)));
    };
    xhr.upload.onload = () => onProgress?.(100);

    xhr.onload = () => {
      signal?.removeEventListener("abort", onAbort);
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as IngestResponse);
        } catch {
          reject(new Error("Invalid ingest response"));
        }
        return;
      }
      reject(parseErrorBody(xhr.responseText, xhr.status, xhr.statusText));
    };
    xhr.onerror = () => {
      signal?.removeEventListener("abort", onAbort);
      reject(new Error("Network error during upload"));
    };
    xhr.onabort = () => {
      signal?.removeEventListener("abort", onAbort);
      reject(new DOMException("Upload aborted", "AbortError"));
    };

    const form = new FormData();
    form.append("file", file, file.name);
    if (docType) form.append("doc_type", docType);
    if (tags && tags.length > 0) form.append("tags", tags.join(","));
    xhr.send(form);
  });
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export async function getHealth(): Promise<HealthResponse> {
  return unwrap(await fetch("/api/health", { cache: "no-store" }));
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export async function listConversations(): Promise<ConversationListResponse> {
  return unwrap(await fetch("/api/conversations", { cache: "no-store" }));
}

export async function getConversationMessages(
  id: string,
): Promise<ConversationMessagesResponse> {
  return unwrap(
    await fetch(`/api/conversations/${encodeURIComponent(id)}/messages`, {
      cache: "no-store",
    }),
  );
}

export async function renameConversation(id: string, title: string): Promise<void> {
  await unwrap<void>(
    await fetch(`/api/conversations/${encodeURIComponent(id)}`, {
      method: "PATCH",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ title }),
    }),
  );
}

export async function deleteConversation(id: string): Promise<void> {
  await unwrap<void>(
    await fetch(`/api/conversations/${encodeURIComponent(id)}`, {
      method: "DELETE",
    }),
  );
}

// ---------------------------------------------------------------------------
// Memory
// ---------------------------------------------------------------------------

export async function listMemoryFacts(): Promise<MemoryFactListResponse> {
  return unwrap(await fetch("/api/memory", { cache: "no-store" }));
}

export async function deleteMemoryFact(id: string): Promise<void> {
  await unwrap<void>(
    await fetch(`/api/memory/${encodeURIComponent(id)}`, { method: "DELETE" }),
  );
}

export async function getConversationMemory(
  id: string,
): Promise<ConversationMemoryResponse> {
  return unwrap(
    await fetch(`/api/memory/conversations/${encodeURIComponent(id)}`, {
      cache: "no-store",
    }),
  );
}

// ---------------------------------------------------------------------------
// Live insights
// ---------------------------------------------------------------------------

export async function getInsights(): Promise<InsightsResponse> {
  return unwrap(await fetch("/api/insights", { cache: "no-store" }));
}
