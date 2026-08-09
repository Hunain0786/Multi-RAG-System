import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * DELETE /api/docs/[id] -> FastAPI DELETE /documents/{id}
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
    `${env.BACKEND_URL}/documents/${encodeURIComponent(id)}`,
    { method: "DELETE", cache: "no-store" },
  );
  if (upstream.status === 204) {
    return new Response(null, { status: 204 });
  }
  const body = await upstream.text();
  const contentType =
    upstream.headers.get("content-type") ?? "application/json";
  if (
    contentType.includes("text/html") ||
    body.trimStart().toLowerCase().startsWith("<!doctype")
  ) {
    return Response.json(
      {
        detail:
          "Backend returned HTML instead of JSON when deleting a document.",
      },
      { status: 502 },
    );
  }
  return new Response(body, {
    status: upstream.status,
    headers: { "content-type": contentType },
  });
}
