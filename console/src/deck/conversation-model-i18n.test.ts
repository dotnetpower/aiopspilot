import { afterEach, describe, expect, it } from "vitest";
import { setLocale } from "../i18n";
import { conversationModelText, conversationT2Label } from "./conversation-model-i18n";

afterEach(() => setLocale("en"));

describe("conversation model copy", () => {
  it("renders English and Korean labels without the shared catalog", () => {
    expect(conversationModelText("label")).toBe("Conversation model");
    setLocale("ko");
    expect(conversationModelText("label")).toBe("대화 모델");
    expect(conversationT2Label("gpt-5.6-sol")).toBe("T2 - gpt-5.6-sol");
  });
});
