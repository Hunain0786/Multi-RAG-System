import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/** GET /api/insights -> FastAPI GET /insights */
export async function GET(): Promise<Response> {
  try {
    const upstream = await fetch(`${env.BACKEND_URL}/insights`, {
      method: "GET",
      cache: "no-store",
      // Insight endpoint runs several SQL scans; give it a generous ceiling.
      signal: AbortSignal.timeout(30_000),
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
        error: (e as Error).message,
        generated_at: new Date().toISOString(),
        counts: { high: 0, med: 0, low: 0, info: 0, good: 0, unknown: 0 },
        items: [],
      },
      { status: 502 },
    );
  }
}
