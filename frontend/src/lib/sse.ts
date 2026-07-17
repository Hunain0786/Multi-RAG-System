import type { SseEvent } from "@/lib/types";

/**
 * Consume an SSE stream from a POST request and yield parsed events.
 *
 * We don't use `EventSource` because it only supports GET. The FastAPI /chat
 * endpoint requires a JSON body, so we roll our own parser on top of
 * `fetch` + `ReadableStream`.
 *
 * SSE frame format (from sse-starlette):
 *   event: <type>\n
 *   data: <json>\n
 *   \n
 */
export async function* streamChat(
  url: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent, void, void> {
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "content-type": "application/json",
      accept: "text/event-stream",
    },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok) {
    const text = await response.text().catch(() => response.statusText);
    throw new Error(
      `chat request failed (${response.status}): ${text.slice(0, 500)}`,
    );
  }
  if (!response.body) {
    throw new Error("chat response had no body");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      // Frames are separated by a blank line. Handle both \n\n and \r\n\r\n.
      let sep: number;
      while ((sep = firstBlankLine(buffer)) !== -1) {
        const raw = buffer.slice(0, sep);
        buffer = buffer.slice(sep + separatorLength(buffer, sep));

        const evt = parseFrame(raw);
        if (evt) yield evt;
      }
    }
    // Flush trailing frame (if any) — most SSE producers end with a blank line
    // so this is defensive.
    if (buffer.trim().length > 0) {
      const evt = parseFrame(buffer);
      if (evt) yield evt;
    }
  } finally {
    reader.releaseLock();
  }
}

function firstBlankLine(s: string): number {
  const a = s.indexOf("\n\n");
  const b = s.indexOf("\r\n\r\n");
  if (a === -1) return b;
  if (b === -1) return a;
  return Math.min(a, b);
}

function separatorLength(s: string, at: number): number {
  return s.startsWith("\r\n\r\n", at) ? 4 : 2;
}

function parseFrame(raw: string): SseEvent | null {
  const lines = raw.split(/\r?\n/);
  const dataParts: string[] = [];
  for (const line of lines) {
    if (line.startsWith("data:")) {
      dataParts.push(line.slice(5).replace(/^ /, ""));
    }
    // We ignore the `event:` line — the JSON payload from run_agent includes
    // its own `type` field, so we trust that.
  }
  if (dataParts.length === 0) return null;
  const dataStr = dataParts.join("\n");
  try {
    const parsed = JSON.parse(dataStr);
    if (parsed && typeof parsed === "object" && typeof parsed.type === "string") {
      return parsed as SseEvent;
    }
    return null;
  } catch {
    return null;
  }
}
