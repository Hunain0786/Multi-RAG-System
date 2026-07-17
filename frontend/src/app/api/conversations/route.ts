import { env } from "@/lib/env";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  const upstream = await fetch(`${env.BACKEND_URL}/conversations`, {
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
