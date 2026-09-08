import type {
  InvocationRecord,
  LlmCostResponse,
} from "./llm-cost";
import type { LlmUsageRange } from "./llm-cost-range";

function summary(
  key: string,
  invocations: number,
  promptTokens: number,
  completionTokens: number,
) {
  return {
    key,
    invocations,
    prompt_tokens: promptTokens,
    completion_tokens: completionTokens,
    total_tokens: promptTokens + completionTokens,
  };
}

export function sampleLlmCost(range: LlmUsageRange): LlmCostResponse {
  const records: readonly InvocationRecord[] = [
    {
      occurred_at: range.from,
      correlation_id: "sample-conversation-1",
      capability_id: "query_inventory",
      model_key: "narrator-small",
      tier: "T1",
      mode: "shadow",
      usage_scope: "operator_chat",
      prompt_tokens: 1480,
      completion_tokens: 420,
      total_tokens: 1900,
    },
    {
      occurred_at: new Date(new Date(range.from).getTime() + 86_400_000).toISOString(),
      correlation_id: "sample-investigation-1",
      capability_id: "incident_rca",
      model_key: "reasoning-large",
      tier: "T2",
      mode: "shadow",
      usage_scope: "investigation",
      prompt_tokens: 3840,
      completion_tokens: 1160,
      total_tokens: 5000,
    },
    {
      occurred_at: new Date(new Date(range.to).getTime() - 3_600_000).toISOString(),
      correlation_id: "sample-conversation-2",
      capability_id: "summarize_evidence",
      model_key: "narrator-small",
      tier: "T1",
      mode: "shadow",
      usage_scope: "operator_chat",
      prompt_tokens: 1720,
      completion_tokens: 580,
      total_tokens: 2300,
    },
  ];
  return {
    source: "sample-preview",
    range_start: range.from,
    range_end: range.to,
    latest_occurred_at: records[2]!.occurred_at,
    invocations: 64,
    total: summary("total", 64, 142400, 37600),
    chat: summary("chat", 48, 86400, 21600),
    by_scope: [
      summary("operator_chat", 48, 86400, 21600),
      summary("investigation", 12, 44800, 12800),
      summary("verification", 4, 11200, 3200),
    ],
    by_model: [
      summary("narrator-small", 52, 101600, 26400),
      summary("reasoning-large", 12, 40800, 11200),
    ],
    chat_by_model: [
      summary("narrator-small", 48, 86400, 21600),
    ],
    by_mode: [
      summary("shadow", 64, 142400, 37600),
    ],
    by_conversation: [
      summary("sample-conversation-1", 24, 42400, 10600),
      summary("sample-conversation-2", 24, 44000, 11000),
    ],
    by_conversation_truncated: false,
    conversation_count: 2,
    by_hour: [
      summary("08", 12, 26800, 7200),
      summary("12", 18, 40200, 9800),
      summary("16", 20, 43800, 11600),
      summary("20", 14, 31600, 9000),
    ],
    by_day: [
      summary(range.from.slice(0, 10), 22, 48200, 12800),
      summary(records[1]!.occurred_at.slice(0, 10), 18, 40600, 10400),
      summary(records[2]!.occurred_at.slice(0, 10), 24, 53600, 14400),
    ],
    by_month: [
      summary(range.from.slice(0, 7), 64, 142400, 37600),
    ],
    records,
    records_truncated: false,
    record_count: records.length,
  };
}
