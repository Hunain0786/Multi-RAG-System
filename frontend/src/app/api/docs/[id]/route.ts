import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * DELETE /api/docs/[id] -> FastAPI DELETE /docs/{id}
 *
 * Next 15+ ships `params` as a Promise; awaiting it is compatible with
 * both 15 and 16.
 */
export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ id: string }> },
): Promise<Response> {
  const { id } = await params;
  const upstream = await fetch(
    `${env.BACKEND_URL}/docs/${encodeURIComponent(id)}`,
    { method: "DELETE", cache: "no-store" },
  );
  if (upstream.status === 204) {
    return new Response(null, { status: 204 });
  }
  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
