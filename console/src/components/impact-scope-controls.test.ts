import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, test } from "vitest";

const mock = readFileSync(
  fileURLToPath(new URL("../../../mocks/ui/blast-radius.html", import.meta.url)),
  "utf8",
);
const mockStyles = readFileSync(
  fileURLToPath(
    new URL(
      "../../../mocks/ui/assets/governance-evidence-workspace.css",
      import.meta.url,
    ),
  ),
  "utf8",
);
const route = readFileSync(
  fileURLToPath(new URL("../routes/blast-radius.tsx", import.meta.url)),
  "utf8",
);
const styles = readFileSync(fileURLToPath(new URL("../styles.css", import.meta.url)), "utf8");

describe("Impact scope controls", () => {
  test("defines the complete control system in the mockup first", () => {
    expect(mock).toContain('class="fg-toolbar" data-fg-static-form');
    expect(mock.match(/class="fg-field"/g)).toHaveLength(3);
    expect(mock).toContain(
      '<button class="fg-button is-primary" type="submit">Simulate impact</button>',
    );
    expect(mockStyles).toContain(".cs-governance-evidence .fg-toolbar");
    expect(mockStyles).toContain(".cs-governance-evidence .fg-field input");
    expect(mockStyles).toContain(".cs-governance-evidence .fg-field select");
    expect(mockStyles).toContain(
      ".cs-governance-evidence .fg-toolbar .fg-button { width: 100%; }",
    );
  });

  test("maps the approved mockup controls into the production route", () => {
    expect(route).toContain('class="impact-query-panel"');
    expect(route).toContain('class="impact-query-input"');
    expect(route).toContain('class="impact-query-check-box"');
    expect(route).toContain('class="btn primary impact-query-submit"');
    expect(route.match(/aria-pressed=\{view === "(impact|map|table)"\}/g)).toHaveLength(3);
    expect(route).toContain('header: t("ontology.blast.columnVerification")');
    expect(route).toContain("verification_status: e.verification_status");
    expect(styles).toContain(".impact-query-check input:checked + .impact-query-check-box");
    expect(styles).toContain(".impact-query-submit:disabled");
    expect(styles).toContain(".impact-query-submit { width: 100%; }");
    expect(styles).toContain(".segmented-control button:focus-visible");
    expect(styles).toContain(".blast-radius-route .segmented-control button { min-height: 44px; }");
    expect(styles).toContain("@media (max-width: 1120px)");
    expect(styles).toContain(".blast-impact-layout { grid-template-columns: 1fr; }");
  });
});
