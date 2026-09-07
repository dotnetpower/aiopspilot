import { describe, expect, it } from "vitest";
import {
  conversationModelStorageKey,
  conversationReplyModel,
  decodeConversationModelAvailability,
  readConversationModelTier,
  writeConversationModelTier,
} from "./conversation-model-selection";

class MemoryStore {
  readonly values = new Map<string, string>();
  getItem(key: string) {
    return this.values.get(key) ?? null;
  }
  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
  removeItem(key: string) {
    this.values.delete(key);
  }
}

describe("conversation model selection", () => {
  it("persists one explicit tier per conversation and removes Auto", () => {
    const store = new MemoryStore();
    writeConversationModelTier(store, "conversation-a", "t2");
    expect(readConversationModelTier(store, "conversation-a")).toBe("t2");
    expect(readConversationModelTier(store, "conversation-b")).toBe("auto");

    writeConversationModelTier(store, "conversation-a", "auto");
    expect(store.values.has(conversationModelStorageKey("conversation-a"))).toBe(false);
  });

  it("admits the active T2 primary independently from action-quality quorum", () => {
    expect(decodeConversationModelAvailability({
      t2_model_policy: {
        quorum_ready: true,
        active_primary: {
          family: "gpt-5",
          publisher: "OpenAI",
          catalog_status: "deployed",
        },
      },
    })).toEqual({ t2Available: true, t2Label: "gpt-5 · OpenAI" });

    expect(decodeConversationModelAvailability({
      t2_model_policy: {
        quorum_ready: false,
        active_primary: {
          family: "gpt-5",
          publisher: "OpenAI",
          catalog_status: "quota-unavailable",
        },
      },
    })).toEqual({ t2Available: true, t2Label: "gpt-5 · OpenAI" });

    expect(decodeConversationModelAvailability({
      t2_model_policy: {
        quorum_ready: true,
        active_primary: null,
      },
    }).t2Available).toBe(false);
  });

  it("shows the T2 response author instead of the unrelated T1 router choice", () => {
    expect(conversationReplyModel("gpt-5.6-sol", "narrator-mini", "t2")).toBe("gpt-5.6-sol");
    expect(conversationReplyModel("narrator-mini", "narrator-fast", "t1")).toBe("narrator-fast");
  });
});
