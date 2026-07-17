import type {
  ConversationListResponse,
  ConversationMemoryResponse,
  ConversationMessagesResponse,
  DocListResponse,
  DocType,
  HealthResponse,
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

// ---------------------------------------------------------------------------
// Docs (read + delete only — ingestion is CLI-only, see `make ingest`)
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
