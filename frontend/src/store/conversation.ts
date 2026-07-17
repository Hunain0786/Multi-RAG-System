"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

import { getConversationMessages } from "@/lib/api";
import { streamChat } from "@/lib/sse";
import type {
  AssistantChatMessage,
  ChatMessage,
  PersistedMessage,
  SseEvent,
  ToolCallState,
  ToolName,
  UserChatMessage,
} from "@/lib/types";

const STORAGE_KEY = "multirag:conversation";

interface ConversationState {
  /** Server-side id. `null` before the first turn; captured from the SSE
   *  `conversation` event emitted at the start of every /chat request. */
  conversationId: string | null;
  messages: ChatMessage[];
  streaming: boolean;
  errorText: string | null;
  send: (prompt: string) => Promise<void>;
  loadConversation: (id: string) => Promise<void>;
  abort: () => void;
  reset: () => void;
  _controller: AbortController | null;
}

function nextId(): string {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export const useConversation = create<ConversationState>()(
  persist(
    (set, get) => ({
      conversationId: null,
      messages: [],
      streaming: false,
      errorText: null,
      _controller: null,

      reset: () => {
        get()._controller?.abort();
        set({
          conversationId: null,
          messages: [],
          streaming: false,
          errorText: null,
          _controller: null,
        });
      },

      abort: () => {
        get()._controller?.abort();
        set({ streaming: false, _controller: null });
      },

      loadConversation: async (id: string) => {
        get()._controller?.abort();
        set({
          streaming: false,
          errorText: null,
          _controller: null,
          messages: [],
          conversationId: id,
        });
        try {
          const res = await getConversationMessages(id);
          const rebuilt = rebuildMessagesFromDb(res.messages);
          set({ messages: rebuilt });
        } catch (e) {
          set({ errorText: `Failed to load conversation: ${(e as Error).message}` });
        }
      },

      send: async (prompt: string) => {
        if (get().streaming) return;

        const userMsg: UserChatMessage = {
          id: nextId(),
          role: "user",
          content: prompt,
          ts: Date.now(),
        };
        const assistantMsg: AssistantChatMessage = {
          id: nextId(),
          role: "assistant",
          content: "",
          toolCalls: [],
          blocks: [],
          streaming: true,
          ts: Date.now(),
        };

        const controller = new AbortController();
        set({
          messages: [...get().messages, userMsg, assistantMsg],
          streaming: true,
          errorText: null,
          _controller: controller,
        });

        const patchAssistant = (
          patch:
            | Partial<AssistantChatMessage>
            | ((prev: AssistantChatMessage) => Partial<AssistantChatMessage>),
        ) => {
          set((state) => ({
            messages: state.messages.map((m) => {
              if (m.id !== assistantMsg.id || m.role !== "assistant") return m;
              const p = typeof patch === "function" ? patch(m) : patch;
              return { ...m, ...p };
            }),
          }));
        };

        try {
          // Backend uses DB history + new user turn — we only send the new one
          // and let Postgres be the source of truth for prior context.
          const stream = streamChat(
            "/api/chat",
            {
              conversation_id: get().conversationId,
              messages: [{ role: "user", content: prompt }],
            },
            controller.signal,
          );
          for await (const evt of stream) {
            if (evt.type === "conversation") {
              set({ conversationId: evt.id });
              continue;
            }
            applyEvent(evt, patchAssistant);
          }
          patchAssistant({ streaming: false });
        } catch (e) {
          const aborted =
            (e as { name?: string }).name === "AbortError" ||
            controller.signal.aborted;
          patchAssistant((prev) => ({
            streaming: false,
            errorText: aborted
              ? "Stopped."
              : `${(e as Error).message ?? "unknown error"}`,
            toolCalls: prev.toolCalls.map((t) =>
              t.status === "running"
                ? {
                    ...t,
                    status: "error",
                    errorText: aborted ? "aborted" : (e as Error).message,
                    finishedAt: Date.now(),
                  }
                : t,
            ),
          }));
          if (!aborted) {
            set({ errorText: (e as Error).message ?? "unknown error" });
          }
        } finally {
          set({ streaming: false, _controller: null });
        }
      },
    }),
    {
      name: STORAGE_KEY,
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        conversationId: state.conversationId,
        messages: state.messages,
      }),
      onRehydrateStorage: () => (state) => {
        if (!state) return;
        state.streaming = false;
        state._controller = null;
        state.errorText = null;
        for (const m of state.messages) {
          if (m.role === "assistant") {
            m.streaming = false;
            for (const t of m.toolCalls) {
              if (t.status === "running") {
                t.status = "error";
                t.errorText = "interrupted (page reload)";
                t.finishedAt = t.finishedAt ?? Date.now();
              }
            }
          }
        }
      },
    },
  ),
);

/** Applies a single SSE event to the current assistant message via patch fn. */
function applyEvent(
  evt: SseEvent,
  patch: (
    p:
      | Partial<AssistantChatMessage>
      | ((prev: AssistantChatMessage) => Partial<AssistantChatMessage>),
  ) => void,
) {
  switch (evt.type) {
    case "conversation":
      // Handled in the caller (updates root state, not per-message state).
      break;

    case "text":
      patch((prev) => {
        const blocks = [...prev.blocks];
        const last = blocks[blocks.length - 1];
        if (last && last.kind === "text") {
          blocks[blocks.length - 1] = {
            kind: "text",
            text: last.text + evt.text,
          };
        } else {
          blocks.push({ kind: "text", text: evt.text });
        }
        return {
          content: prev.content + evt.text,
          blocks,
        };
      });
      break;

    case "tool_use": {
      const tc: ToolCallState = {
        id: evt.id,
        name: evt.name as ToolName,
        input: evt.input,
        status: "running",
        startedAt: Date.now(),
      };
      patch((prev) => ({
        toolCalls: [...prev.toolCalls, tc],
        blocks: [...prev.blocks, { kind: "tool", toolCallId: evt.id }],
      }));
      break;
    }

    case "tool_result":
      patch((prev) => ({
        toolCalls: prev.toolCalls.map((t) =>
          t.id === evt.tool_use_id
            ? {
                ...t,
                status: evt.is_error ? "error" : "done",
                result: evt.result,
                errorText: evt.is_error ? String(evt.result) : undefined,
                finishedAt: Date.now(),
              }
            : t,
        ),
      }));
      break;

    case "stop":
      patch({ streaming: false });
      break;

    case "error":
      patch((prev) => ({
        streaming: false,
        errorText: prev.errorText
          ? `${prev.errorText}; ${evt.message}`
          : evt.message,
      }));
      break;
  }
}

/**
 * Rebuild the frontend ChatMessage[] from Postgres rows. Preserves interleaved
 * text/tool blocks and pairs tool_use blocks with the tool_result blocks that
 * arrived in the subsequent user turn.
 *
 * User turns whose content is only tool_result blocks are hidden (they're an
 * internal detail of the tool-use loop, not something the human sent).
 */
function rebuildMessagesFromDb(rows: PersistedMessage[]): ChatMessage[] {
  const messages: ChatMessage[] = [];
  const toolCallIndex = new Map<string, ToolCallState>();

  for (const row of rows) {
    if (row.role === "user") {
      const textParts: string[] = [];
      const toolResults: Array<{
        tool_use_id: string;
        content: unknown;
        is_error: boolean;
      }> = [];

      for (const block of row.content) {
        const t = block["type"];
        if (t === "text") {
          textParts.push(String(block["text"] ?? ""));
        } else if (t === "tool_result") {
          toolResults.push({
            tool_use_id: String(block["tool_use_id"] ?? ""),
            content: block["content"],
            is_error: Boolean(block["is_error"]),
          });
        }
      }

      // Attach each tool_result back to the tool_use it belongs to.
      for (const tr of toolResults) {
        const call = toolCallIndex.get(tr.tool_use_id);
        if (!call) continue;
        const resultBody = extractToolResultBody(tr.content);
        call.status = tr.is_error ? "error" : "done";
        call.result = tr.is_error ? undefined : resultBody;
        call.errorText = tr.is_error ? String(resultBody) : undefined;
        call.finishedAt = new Date(row.created_at).getTime();
      }

      const humanText = textParts.join("").trim();
      if (humanText.length > 0) {
        messages.push({
          id: row.id,
          role: "user",
          content: humanText,
          ts: new Date(row.created_at).getTime(),
        });
      }
      continue;
    }

    // assistant
    const toolCalls: ToolCallState[] = [];
    const blocks: AssistantChatMessage["blocks"] = [];
    let contentText = "";
    for (const block of row.content) {
      const t = block["type"];
      if (t === "text") {
        const text = String(block["text"] ?? "");
        contentText += text;
        const last = blocks[blocks.length - 1];
        if (last && last.kind === "text") {
          blocks[blocks.length - 1] = { kind: "text", text: last.text + text };
        } else {
          blocks.push({ kind: "text", text });
        }
      } else if (t === "tool_use") {
        const id = String(block["id"] ?? "");
        const name = String(block["name"] ?? "") as ToolName;
        const input = (block["input"] ?? {}) as Record<string, unknown>;
        const tc: ToolCallState = {
          id,
          name,
          input,
          status: "running",
          startedAt: new Date(row.created_at).getTime(),
        };
        toolCalls.push(tc);
        toolCallIndex.set(id, tc);
        blocks.push({ kind: "tool", toolCallId: id });
      }
    }

    messages.push({
      id: row.id,
      role: "assistant",
      content: contentText,
      toolCalls,
      blocks,
      streaming: false,
      ts: new Date(row.created_at).getTime(),
    });
  }

  return messages;
}

/**
 * Tool results are stored as `content: [{type:"text", text: "<json>"}]` in the
 * DB. Try to parse the JSON back into an object so renderers work; fall back to
 * the raw string.
 */
function extractToolResultBody(content: unknown): unknown {
  if (Array.isArray(content)) {
    const first = content[0] as { type?: string; text?: string } | undefined;
    if (first && first.type === "text" && typeof first.text === "string") {
      try {
        return JSON.parse(first.text);
      } catch {
        return first.text;
      }
    }
  }
  return content;
}
