import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Proxies POST /api/chat -> FastAPI POST /chat and pipes the SSE response back
 * through unchanged. Keeps BACKEND_URL server-side so the browser never talks
 * to :8000 directly.
 */
export async function POST(req: Request): Promise<Response> {
  const upstream = await fetch(`${env.BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: await req.text(),
    // Node fetch buffers when consumer is slow; disabling any implicit caching.
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    const detail = await upstream.text().catch(() => upstream.statusText);
    return new Response(
      JSON.stringify({ error: detail || upstream.statusText }),
      {
        status: upstream.status || 502,
        headers: { "content-type": "application/json" },
      },
    );
  }

  return new Response(upstream.body, {
    headers: {
      "content-type": "text/event-stream; charset=utf-8",
      "cache-control": "no-cache, no-transform",
      connection: "keep-alive",
      // Nginx/Vercel: don't buffer.
      "x-accel-buffering": "no",
    },
  });
}
