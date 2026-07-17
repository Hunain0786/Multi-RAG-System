import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/docs?doc_type=... -> FastAPI GET /docs.
 *
 * Note: there is NO POST handler. Document ingestion is intentionally
 * code-only — see `make ingest` / `python -m multirag.rag.pipeline`. Keeping
 * the corpus curated is a design choice: the LLM cannot ingest new documents
 * either (the `ingest_doc` tool is not registered).
 */
export async function GET(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const qs = url.search; // preserves ?doc_type=... verbatim
  const upstream = await fetch(`${env.BACKEND_URL}/docs${qs}`, {
    method: "GET",
    cache: "no-store",
  });
  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
