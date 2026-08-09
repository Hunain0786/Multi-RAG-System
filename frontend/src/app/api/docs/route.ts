import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * GET /api/docs?doc_type=... -> FastAPI GET /docs
 * POST /api/docs             -> FastAPI POST /docs/ingest (multipart)
 *
 * The agent still cannot ingest documents (`ingest_doc` is not registered);
 * this endpoint is for operators via the /docs UI.
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

  const upstream = await fetch(`${env.BACKEND_URL}/docs/ingest`, {
    method: "POST",
    body: outgoing,
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
