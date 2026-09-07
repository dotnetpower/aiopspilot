import { describe, expect, test } from "vitest";
import { sampleLlmCost } from "./llm-cost.sample";

describe("LLM cost Sample projection", () => {
  test("uses the requested window and exposes no pricing", () => {
    const data = sampleLlmCost({
      preset: "7d",
      from: "2026-08-25T00:00:00.000Z",
      to: "2026-09-01T00:00:00.000Z",
    });

    expect(data.source).toBe("sample-preview");
    expect(data.range_start).toBe("2026-08-25T00:00:00.000Z");
    expect(data.range_end).toBe("2026-09-01T00:00:00.000Z");
    expect(data.total.total_tokens).toBe(180000);
    expect(data.total).not.toHaveProperty("cost");
    expect(data.records.every((record) => !Object.hasOwn(record, "cost"))).toBe(true);
  });
});
