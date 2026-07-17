import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

async function proxy(id: string, init: RequestInit): Promise<Response> {
  const upstream = await fetch(
    `${env.BACKEND_URL}/conversations/${encodeURIComponent(id)}`,
    init,
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

interface Ctx {
  params: Promise<{ id: string }>;
}

export async function PATCH(req: Request, ctx: Ctx): Promise<Response> {
  const { id } = await ctx.params;
  return proxy(id, {
    method: "PATCH",
    headers: { "content-type": "application/json" },
    body: await req.text(),
  });
}

export async function DELETE(_req: Request, ctx: Ctx): Promise<Response> {
  const { id } = await ctx.params;
  return proxy(id, { method: "DELETE" });
}
