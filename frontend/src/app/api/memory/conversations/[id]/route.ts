import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

interface Ctx {
  params: Promise<{ id: string }>;
}

export async function GET(_req: Request, ctx: Ctx): Promise<Response> {
  const { id } = await ctx.params;
  const upstream = await fetch(
    `${env.BACKEND_URL}/memory/conversations/${encodeURIComponent(id)}`,
    { method: "GET", cache: "no-store" },
  );
  const body = await upstream.text();
  return new Response(body, {
    status: upstream.status,
    headers: {
      "content-type":
        upstream.headers.get("content-type") ?? "application/json",
    },
  });
}
