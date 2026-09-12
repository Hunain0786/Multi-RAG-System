/**
 * SSE event union — mirrors backend/src/multirag/agent/loop.py exactly.
 * Every event arrives as `event: <type>\ndata: <json>\n\n` from FastAPI's sse-starlette.
 */
export type SseEvent =
  | { type: "conversation"; id: string; created: boolean }
  | { type: "text"; text: string }
  | {
      type: "tool_use";
      id: string;
      name: ToolName;
      input: Record<string, unknown>;
    }
  | {
      type: "tool_result";
      tool_use_id: string;
      name: ToolName;
      is_error: boolean;
      result: unknown;
    }
  | { type: "stop"; reason: string; step: number }
  | { type: "error"; message: string };

export type ToolName =
  | "compile_metric"
  | "compile_composite"
  | "search_docs"
  | "list_catalog"
  | "list_metrics"
  | "query_postgres"
  | "remember"
  | "recall"
  | "forget";

/** ------------------------------------------------------------------
 * Tool-result shapes — kept 1:1 with backend/src/multirag/agent/tools/*.
 * ------------------------------------------------------------------ */

export type MetricFormat =
  | "integer"
  | "percentage"
  | "number"
  | "days"
  | "currency_usd"
  | "string";

export type ChartType = "bar" | "line" | "area" | "pie" | "table" | "kpi";

export interface CompiledColumn {
  name: string;
  label: string;
  format: MetricFormat;
}

export interface CompileMetricResult {
  metric: string;
  domain: string;
  columns: CompiledColumn[];
  rows: Array<Record<string, unknown>>;
  sql: string;
  chart_hint: { type: ChartType; x_key: string | null };
  pagination: {
    limit: number;
    offset: number;
    next_offset: number;
    has_more: boolean;
    total_returned: number;
  };
}

export interface CompileCompositeResult {
  domain: string;
  columns: CompiledColumn[];
  row: Record<string, unknown>;
  sql: string;
}

export interface QueryPostgresResult {
  sql: string;
  row_count: number;
  rows: Array<Record<string, unknown>>;
}

export type DocType = "policy" | "manual" | "faq" | "other";

export interface SearchHit {
  doc_id: string;
  chunk_index: number;
  source_path: string;
  doc_type: DocType;
  score: number;
  text: string;
  tags: string[];
}

export interface SearchDocsResult {
  query: string;
  hits: SearchHit[];
}

export interface ListCatalogResult {
  catalog: string;
}

export interface MetricCatalogEntry {
  name: string;
  domain: string;
  label: string;
  description: string;
  format: MetricFormat;
  chart_hint: { type: ChartType; x_key: string | null };
  example_use?: string;
}

export interface ListMetricsResult {
  metrics: MetricCatalogEntry[];
}

/** ------------------------------------------------------------------
 * Memory-tool result shapes — mirror backend/src/multirag/agent/tools/*.
 * ------------------------------------------------------------------ */

export type FactKind = "preference" | "fact" | "constraint";

export interface RememberResult {
  id: string;
  text: string;
  kind: FactKind;
  created_at: string;
}

export interface RecallHit {
  id: string;
  text: string;
  kind: FactKind;
  similarity: number;
  created_at: string;
}

export interface RecallResult {
  query: string;
  hits: RecallHit[];
}

export interface ForgetResult {
  id: string;
  deleted: boolean;
  reason?: string;
}

/** ------------------------------------------------------------------
 * Conversation state — what we store per assistant message.
 * ------------------------------------------------------------------ */

export interface ToolCallState {
  id: string;
  name: ToolName;
  input: unknown;
  status: "running" | "done" | "error";
  result?: unknown;
  errorText?: string;
  startedAt: number;
  finishedAt?: number;
}

export type ChatRole = "user" | "assistant";

export interface UserChatMessage {
  id: string;
  role: "user";
  content: string;
  ts: number;
}

export interface AssistantChatMessage {
  id: string;
  role: "assistant";
  content: string;
  toolCalls: ToolCallState[];
  /** Preserves the interleaving order of text vs. tool_use as they arrive. */
  blocks: Array<
    { kind: "text"; text: string } | { kind: "tool"; toolCallId: string }
  >;
  streaming: boolean;
  errorText?: string;
  ts: number;
}

export type ChatMessage = UserChatMessage | AssistantChatMessage;

/** ------------------------------------------------------------------
 * Docs API — list / delete / ingest (multipart upload via /api/docs).
 * ------------------------------------------------------------------ */

export interface DocSummary {
  id: string;
  source_path: string;
  doc_type: DocType;
  sha256: string;
  chunk_count: number;
  tokens: number;
  ingested_at: string; // ISO date
  meta: Record<string, unknown>;
}

export interface DocListResponse {
  docs: DocSummary[];
  total: number;
}

export interface IngestResponse {
  doc_id: string;
  chunks_added: number;
  tokens: number;
  reused: boolean;
  source_path: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  postgres: boolean;
  pinecone: boolean;
  pinecone_stats: {
    namespaces?: string[];
    total_vector_count?: number;
    postgres_error?: string;
    pinecone_error?: string;
  };
}

/** ------------------------------------------------------------------
 * Conversation & memory API shapes — mirror backend/schemas/memory.py.
 * ------------------------------------------------------------------ */

export interface ConversationSummary {
  id: string;
  user_id: string;
  title: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ConversationListResponse {
  conversations: ConversationSummary[];
  total: number;
}

/** A message row as it lives in Postgres — content is a list of content blocks. */
export interface PersistedMessage {
  id: string;
  seq: number;
  role: ChatRole;
  content: Array<Record<string, unknown>>;
  created_at: string;
}

export interface ConversationMessagesResponse {
  conversation_id: string;
  messages: PersistedMessage[];
}

export interface MemoryFactSummary {
  id: string;
  user_id: string;
  text: string;
  kind: FactKind;
  confidence: number;
  source_conversation_id: string | null;
  created_at: string;
}

export interface MemoryFactListResponse {
  facts: MemoryFactSummary[];
  total: number;
}

export interface EpisodeSummary {
  id: string;
  conversation_id: string;
  from_seq: number;
  to_seq: number;
  summary: string;
  created_at: string;
}

export interface ConversationMemoryResponse {
  conversation_id: string;
  latest_episode: EpisodeSummary | null;
}

/** ------------------------------------------------------------------
 * Live insights — mirrors backend/src/multirag/insights/engine.py.
 * ------------------------------------------------------------------ */

export type InsightSeverity =
  | "good"
  | "info"
  | "low"
  | "med"
  | "high"
  | "unknown";

export type InsightCategory = "sales" | "inventory" | "finance" | "hr" | "ops";

export interface Insight {
  id: string;
  severity: InsightSeverity;
  category: InsightCategory | string;
  title: string;
  detail: string;
  metric: string | null;
  value: number | null;
  prior_value: number | null;
  delta_pct: number | null;
  unit: MetricFormat | string | null;
  generated_at: string;
}

export interface InsightsResponse {
  generated_at: string;
  counts: Record<InsightSeverity, number>;
  items: Insight[];
}
