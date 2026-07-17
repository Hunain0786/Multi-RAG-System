import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** GET /api/health -> FastAPI GET /health */
export async function GET(): Promise<Response> {
  try {
    const upstream = await fetch(`${env.BACKEND_URL}/health`, {
      method: "GET",
      cache: "no-store",
      // Short deadline so the header pill never blocks the page.
      signal: AbortSignal.timeout(4000),
    });
    const body = await upstream.text();
    return new Response(body, {
      status: upstream.status,
      headers: {
        "content-type":
          upstream.headers.get("content-type") ?? "application/json",
      },
    });
  } catch (e) {
    return Response.json(
      {
        status: "degraded",
        postgres: false,
        pinecone: false,
        pinecone_stats: { pinecone_error: (e as Error).message },
      },
      { status: 200 },
    );
  }
}
