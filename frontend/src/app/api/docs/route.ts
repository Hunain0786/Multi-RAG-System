import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/docs?doc_type=... -> FastAPI GET /documents
 * POST /api/docs             -> FastAPI POST /documents/ingest (multipart)
 *
 * Upstream path is `/documents` (not `/docs`) so FastAPI Swagger UI cannot
 * shadow the library API.
 */
function passthrough(upstream: Response, body: string): Response {
  const contentType =
    upstream.headers.get("content-type") ?? "application/json";
  // Guard: if the backend ever returns HTML (e.g. wrong path → Swagger),
  // surface a clear JSON error instead of breaking the client JSON parse.
  if (
    contentType.includes("text/html") ||
    body.trimStart().toLowerCase().startsWith("<!doctype") ||
    body.trimStart().toLowerCase().startsWith("<html")
  ) {
    return Response.json(
      {
        detail:
          "Backend returned HTML instead of JSON for the documents API. " +
          "Expected /documents — check BACKEND_URL and that the backend is up to date.",
      },
      { status: 502 },
    );
  }
  return new Response(body, {
    status: upstream.status,
    headers: { "content-type": contentType },
  });
}

export async function GET(req: Request): Promise<Response> {
  const url = new URL(req.url);
  const qs = url.search; // preserves ?doc_type=... verbatim
  const upstream = await fetch(`${env.BACKEND_URL}/documents${qs}`, {
    method: "GET",
    cache: "no-store",
  });
  const body = await upstream.text();
  return passthrough(upstream, body);
}

export async function POST(req: Request): Promise<Response> {
  const incoming = await req.formData();
  const outgoing = new FormData();

  for (const [key, value] of incoming.entries()) {
    if (typeof value === "string") {
      // Drop empty / auto doc_type so FastAPI treats it as omitted.
      if (key === "doc_type" && (!value.trim() || value.trim() === "auto")) {
        continue;
      }
      outgoing.append(key, value);
      continue;
    }

    const blob = value as File;
    const name =
      blob.name && blob.name !== "blob" ? blob.name : "upload.bin";
    outgoing.append(key, blob, name);
  }

  const upstream = await fetch(`${env.BACKEND_URL}/documents/ingest`, {
    method: "POST",
    body: outgoing,
    cache: "no-store",
  });
  const body = await upstream.text();
  return passthrough(upstream, body);
}
