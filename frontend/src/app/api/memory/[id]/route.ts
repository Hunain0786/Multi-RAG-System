import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface Ctx {
  params: Promise<{ id: string }>;
}

export async function DELETE(_req: Request, ctx: Ctx): Promise<Response> {
  const { id } = await ctx.params;
  const upstream = await fetch(
    `${env.BACKEND_URL}/memory/${encodeURIComponent(id)}`,
    { method: "DELETE" },
  );
  const body = await upstream.text();
  return new Response(body || null, {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
