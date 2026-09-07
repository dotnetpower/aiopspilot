export type ConversationModelTier = "auto" | "t1" | "t2";

export interface ConversationModelAvailability {
  readonly t2Available: boolean;
  readonly t2Label: string | null;
}

const STORAGE_PREFIX = "fdai.deck.model-tier.v1";

export function conversationModelStorageKey(sessionKey: string): string {
  return `${STORAGE_PREFIX}::${sessionKey}`;
}

export function readConversationModelTier(
  store: Pick<Storage, "getItem"> | null,
  sessionKey: string,
): ConversationModelTier {
  const value = store?.getItem(conversationModelStorageKey(sessionKey));
  return value === "t1" || value === "t2" ? value : "auto";
}

export function writeConversationModelTier(
  store: Pick<Storage, "setItem" | "removeItem"> | null,
  sessionKey: string,
  tier: ConversationModelTier,
): void {
  if (store === null) return;
  const key = conversationModelStorageKey(sessionKey);
  if (tier === "auto") {
    store.removeItem(key);
    return;
  }
  store.setItem(key, tier);
}

export function decodeConversationModelAvailability(
  value: unknown,
): ConversationModelAvailability {
  if (typeof value !== "object" || value === null) {
    return { t2Available: false, t2Label: null };
  }
  const policy = (value as Record<string, unknown>).t2_model_policy;
  if (typeof policy !== "object" || policy === null) {
    return { t2Available: false, t2Label: null };
  }
  const record = policy as Record<string, unknown>;
  const active = record.active_primary;
  if (typeof active !== "object" || active === null) {
    return { t2Available: false, t2Label: null };
  }
  const choice = active as Record<string, unknown>;
  const family = typeof choice.family === "string" ? choice.family.trim() : "";
  const publisher = typeof choice.publisher === "string" ? choice.publisher.trim() : "";
  if (!family || !publisher) {
    return { t2Available: false, t2Label: null };
  }
  return { t2Available: true, t2Label: `${family} · ${publisher}` };
}

export function conversationReplyModel(
  responseModel: string,
  t1RouterModel: string | undefined,
  tier: "t1" | "t2" | undefined,
): string {
  return tier === "t2" ? responseModel : t1RouterModel || responseModel;
}
