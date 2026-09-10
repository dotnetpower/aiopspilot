const assert = require("node:assert/strict");
const { existsSync, readFileSync, readdirSync } = require("node:fs");
const { basename, join } = require("node:path");
const test = require("node:test");

const repoRoot = join(__dirname, "..", "..", "..");
const uiRoot = join(repoRoot, "mocks", "ui");
const panelRegistry = readFileSync(join(repoRoot, "console", "src", "panels.tsx"), "utf8");
const masterLanding = readFileSync(join(repoRoot, "index.html"), "utf8");
const nestedLanding = readFileSync(join(uiRoot, "index.html"), "utf8");
const navigation = readFileSync(join(uiRoot, "assets", "calm-slate.js"), "utf8");
const parityScript = readFileSync(join(uiRoot, "assets", "console-parity.js"), "utf8");
const parityStyles = readFileSync(join(uiRoot, "assets", "console-parity.css"), "utf8");
const sharedStyles = readFileSync(join(uiRoot, "assets", "calm-slate.css"), "utf8");
const governanceEvidenceStyles = readFileSync(
  join(uiRoot, "assets", "governance-evidence-workspace.css"),
  "utf8",
);
const knowledgeGraph = readFileSync(join(uiRoot, "ontology-knowledge-graph.html"), "utf8");
const settingsMocks = [
  "settings.html",
  "settings-models.html",
  "settings-runtime.html",
  "settings-memory.html",
  "settings-iam.html",
  "settings-integrations.html",
  "settings-diagnostics.html",
];
const governanceEvidenceMocks = [
  "ontology.html",
  "handover.html",
  "rules.html",
  "workflow-builder.html",
  "capabilities.html",
  "skills.html",
  "blast-radius.html",
  "promotion.html",
  "context-selection-comparisons.html",
  "scope.html",
  "audit.html",
  "browser-evidence.html",
  "forecast-learning.html",
  "conversation-search.html",
  "conversation-assurance.html",
  "reports.html",
  "rule-trace.html",
  "rca.html",
  "documents.html",
];

const consoleNav = masterLanding.slice(
  masterLanding.indexOf('<nav class="console-groups"'),
  masterLanding.indexOf("</nav>", masterLanding.indexOf('<nav class="console-groups"')),
);
const consoleMockPaths = Array.from(
  consoleNav.matchAll(/data-page="(mocks\/ui\/[^"]+\.html)"/g),
  (match) => match[1],
);

const filenameAliases = {
  "agents-constellation": "pantheon",
  "hil": "hil-queue",
  "promotion": "promotion-gates",
  "rule-trace": "trace",
  "settings": "settings-general",
};

function mockPanelId(path) {
  const file = basename(path, ".html");
  return filenameAliases[file] || file;
}

function consolePanelIds() {
  const core = panelRegistry.slice(
    panelRegistry.indexOf("export const CORE_PANELS"),
    panelRegistry.indexOf("export const EXTRA_PANELS"),
  );
  const ids = Array.from(core.matchAll(/\bid: "([a-z0-9-]+)"/g), (match) => match[1]);
  ids.push(...Array.from(
    core.matchAll(/knowledgeSourcePanel\("([a-z0-9-]+)"/g),
    (match) => match[1],
  ));
  ids.push("dashboard");
  return ids.sort();
}

function consolePanelGroups() {
  const registry = panelRegistry.slice(
    panelRegistry.indexOf("const DASHBOARD_PANEL"),
    panelRegistry.indexOf("export const EXTRA_PANELS"),
  );
  const groups = new Map(Array.from(
    registry.matchAll(/\bid: "([a-z0-9-]+)",[\s\S]*?\bgroup: "([a-z]+)"/g),
    (match) => [match[1], match[2]],
  ));
  Array.from(
    registry.matchAll(/knowledgeSourcePanel\("([a-z0-9-]+)"/g),
    (match) => match[1],
  ).forEach((id) => groups.set(id, "knowledge"));
  return groups;
}

function mockPanelIds() {
  return consoleMockPaths.map(mockPanelId).sort();
}

test("master mock navigation mirrors every production Console panel", () => {
  assert.equal(consoleMockPaths.length, 58);
  assert.equal(new Set(consoleMockPaths).size, 58);
  assert.deepEqual(mockPanelIds(), consolePanelIds());
  consoleMockPaths.forEach((path) => {
    assert.ok(existsSync(join(repoRoot, path)), `missing Console mock: ${path}`);
  });
});

test("master mock navigation follows the Console group hierarchy", () => {
  const consoleGroups = consolePanelGroups();
  const mockGroups = new Map();
  const groups = Array.from(
    consoleNav.matchAll(/<section class="nav-group"[^>]*>([\s\S]*?)<\/section>/g),
    (match) => {
      const label = match[1].match(/class="nav-group-label">([^<]+)</)?.[1];
      const paths = Array.from(
        match[1].matchAll(/data-page="(mocks\/ui\/[^"]+\.html)"/g),
        (item) => item[1],
      );
      paths.forEach((path) => mockGroups.set(mockPanelId(path), label.toLowerCase()));
      const count = paths.length;
      return [label, count];
    },
  );
  assert.deepEqual(groups, [
    ["Overview", 8],
    ["Operations", 14],
    ["Agents", 3],
    ["Governance", 11],
    ["Knowledge", 5],
    ["Evidence", 9],
    ["Labs", 1],
    ["Settings", 7],
  ]);
  assert.deepEqual(
    Array.from(mockGroups).sort(([left], [right]) => left.localeCompare(right)),
    Array.from(consoleGroups).sort(([left], [right]) => left.localeCompare(right)),
  );
});

test("master navigation exposes every local design mock without duplicate destinations", () => {
  const masterMarkup = masterLanding.slice(0, masterLanding.indexOf("<script>"));
  const paths = Array.from(masterMarkup.matchAll(/data-page="([^"]+)"/g), (match) => match[1]);
  assert.equal(paths.length, 96);
  assert.equal(new Set(paths).size, 96);
  assert.equal(paths.length - consoleMockPaths.length, 38);
  paths.forEach((path) => {
    assert.ok(existsSync(join(repoRoot, path)), `missing design mock: ${path}`);
  });
});

test("nested and direct mock navigation expose the same Console destinations", () => {
  const nestedPaths = Array.from(nestedLanding.matchAll(/data-page="([^"]+\.html)"/g), (match) => match[1]);
  const directNavigationBlock = navigation.slice(
    navigation.indexOf("var navigationGroups ="),
    navigation.indexOf("function currentNavigationContext"),
  );
  const directPaths = Array.from(directNavigationBlock.matchAll(/\["([^"]+\.html)",/g), (match) => match[1]);
  const expected = consoleMockPaths.map((path) => path.replace("mocks/ui/", ""));

  expected.forEach((path) => {
    assert.ok(nestedPaths.includes(path), `nested index missing ${path}`);
    assert.ok(directPaths.includes(path), `direct mock navigation missing ${path}`);
  });
  assert.equal(new Set(directPaths).size, 80);
});

test("every parity wrapper resolves to a rendered specification", () => {
  const wrappers = readdirSync(uiRoot)
    .filter((file) => file.endsWith(".html"))
    .map((file) => [file, readFileSync(join(uiRoot, file), "utf8")])
    .filter(([, html]) => html.includes("data-console-parity-page"));

  assert.equal(wrappers.length, 17);
  wrappers.forEach(([file, html]) => {
    const pageId = html.match(/data-console-page="([^"]+)"/)?.[1];
    assert.ok(pageId, `${file} is missing a Console page id`);
    assert.match(parityScript, new RegExp(`"${pageId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}":`));
    assert.match(html, /assets\/console-parity\.css/);
    assert.match(html, /assets\/console-parity\.js/);
    assert.match(html, /assets\/calm-slate\.css/);
    assert.match(html, /assets\/calm-slate\.js/);
  });
});

test("twenty shared polish passes cover every Calm Slate mock", () => {
  const passes = Array.from(sharedStyles.matchAll(/\/\* (\d{2})\./g), (match) => match[1]);
  assert.deepEqual(passes.slice(-20), Array.from({ length: 20 }, (_, index) => String(index + 1).padStart(2, "0")));
  assert.match(sharedStyles, /prefers-reduced-motion: reduce/);
  assert.match(sharedStyles, /:focus-visible/);
  assert.match(sharedStyles, /@media print/);
  assert.match(parityStyles, /@media \(max-width: 520px\)/);
  assert.match(parityStyles, /\.cp-table td::before/);
});

test("master navigation can filter all mock families without losing the active route", () => {
  assert.match(masterLanding, /data-nav-search/);
  assert.match(masterLanding, /function filterNavigation\(query\)/);
  assert.match(masterLanding, /if \(!normalized\) revealPageGroup\(currentPage\)/);
  assert.match(masterLanding, /navSearch\.placeholder = 'Filter ' \+ items\.length \+ ' design mocks'/);
});

test("master navigation uses a Console-like collapsible Activity Bar and Explorer", () => {
  const railTargets = Array.from(
    masterLanding.matchAll(/data-nav-target="([^"]+)"/g),
    (match) => match[1],
  );
  assert.deepEqual(railTargets, [
    "overview",
    "operations",
    "agents",
    "governance",
    "knowledge",
    "evidence",
    "design-collections",
    "labs",
    "settings",
  ]);
  assert.match(masterLanding, /class="activity-bar"/);
  assert.match(masterLanding, /class="side" id="master-nav"/);
  assert.match(masterLanding, /function setNavigationOpen\(open\)/);
  assert.match(masterLanding, /app\.classList\.toggle\('is-nav-collapsed', !open\)/);
  assert.match(masterLanding, /side\.inert = !open/);
  assert.match(masterLanding, /aria-controls="master-nav"/);
  assert.match(masterLanding, /prefers-reduced-motion: reduce/);
});

test("knowledge graph renders every generated ontology node kind", () => {
  assert.match(knowledgeGraph, /function_type:\{label:"FunctionType",fill:/);
  assert.match(knowledgeGraph, /interface_type:\{label:"InterfaceType",fill:/);
  assert.match(knowledgeGraph, /nodeStyles\[node\.kind\]\|\|\{fill:"#6e747b"\}/);
});

test("Governance and Evidence mocks share the refined workspace while Architecture stays unchanged", () => {
  governanceEvidenceMocks.forEach((file) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /governance-evidence-workspace\.css/, `${file} is missing the shared workspace`);
    assert.match(html, /<body class="[^"]*cs-governance-evidence/, `${file} is missing the shared workspace class`);
  });
  assert.doesNotMatch(
    readFileSync(join(uiRoot, "architecture.html"), "utf8"),
    /governance-evidence-workspace\.css|cs-governance-evidence/,
  );
});

test("Ontology mock mirrors the Console semantic-model workbench", () => {
  const ontology = readFileSync(join(uiRoot, "ontology.html"), "utf8");
  const ontologyPreview = readFileSync(join(uiRoot, "assets", "ontology-semantic-preview.js"), "utf8");
  assert.match(ontology, /data-ontology-tab="map"/);
  assert.match(ontology, /data-ontology-lens="relationship"/);
  assert.match(ontology, /data-ontology-bands/);
  assert.match(ontology, /data-ontology-inspector/);
  assert.match(ontologyPreview, /BusinessCapability/);
  assert.match(ontologyPreview, /ObservedOutcome/);
  assert.match(ontologyPreview, /mutation authority/i);
});

test("Audit and catalog-backed Governance and Evidence mocks expose review workspaces", () => {
  const audit = readFileSync(join(uiRoot, "audit.html"), "utf8");
  assert.match(audit, /audit-workbench/);
  assert.match(audit, /focused-final-workspaces\.css/);
  [
    "audit",
    "capabilities",
    "skills",
    "context-selection-comparisons",
    "scope",
    "browser-evidence",
    "forecast-learning",
    "conversation-search",
    "conversation-assurance",
    "reports",
    "documents",
  ].forEach((pageId) => {
    assert.match(
      parityScript,
      new RegExp(`"${pageId.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}": \\{[\\s\\S]*?type: "workspace"`),
      `${pageId} must expose a selected-record workspace`,
    );
  });
  assert.match(parityScript, /code\("storage\.public-blob\.deny", "rule-trace\.html\?correlation=/);
  assert.match(parityScript, /link\("Observed", "audit\.html\?record=/);
});

test("five focused Governance and Evidence mocks use selectable review workspaces", () => {
  const focusedPages = {
    "handover.html": [/oversight-workbench/, /data-oversight-agent/, /Fixed agents/],
    "workflow-builder.html": [/workflow-workbench/, /data-fg-select="workflow-step"/, /Published definition/],
    "blast-radius.html": [/impact-workbench/, /data-fg-select="impact"/, /Unknown coverage/],
    "promotion.html": [/promotion-workbench/, /data-fg-select="promotion"/, /Zero policy escapes/],
    "rule-trace.html": [/trace-workbench/, /data-fg-select="trace"/, /Read-only reconstruction/],
  };
  Object.entries(focusedPages).forEach(([file, patterns]) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /focused-governance-workspaces\.css/);
    assert.match(html, /focused-governance-workspaces\.js/);
    patterns.forEach((pattern) => assert.match(html, pattern, `${file} is missing ${pattern}`));
  });
  const handover = readFileSync(join(uiRoot, "handover.html"), "utf8");
  assert.equal((handover.match(/data-oversight-agent(?:\s|>)/g) || []).length, 15);
  const interactions = readFileSync(join(uiRoot, "assets", "focused-governance-workspaces.js"), "utf8");
  assert.match(interactions, /function activate\(group, value\)/);
  assert.match(interactions, /function bindOversight\(\)/);
});

test("second focused batch visualizes each domain instead of generic tables", () => {
  const focusedPages = {
    "context-selection-comparisons.html": [/context-workbench/, /context-columns/, /Pinned preserved/],
    "scope.html": [/scope-workbench/, /scope-axis is-action/, /Observation is not authority/],
    "conversation-assurance.html": [/assurance-workbench/, /assurance-score-track/, /Original answer is immutable/],
    "forecast-learning.html": [/forecast-workbench/, /forecast-stages/, /Outcome-closed learning/],
    "reports.html": [/reports-workbench/, /report-widget-grid/, /Weekly operations review/],
  };
  Object.entries(focusedPages).forEach(([file, patterns]) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /focused-evidence-workspaces\.css/);
    assert.match(html, /focused-governance-workspaces\.js/);
    patterns.forEach((pattern) => assert.match(html, pattern, `${file} is missing ${pattern}`));
  });
});

test("third focused batch exposes contract and custody review workflows", () => {
  const focusedPages = {
    "capabilities.html": [/catalog-workbench/, /Independent contract axes/, /Declaration only/],
    "skills.html": [/skill-dependency/, /Eligibility chain/, /Composition metadata/],
    "browser-evidence.html": [/custody-workbench/, /custody-timeline/, /Payload not exposed/],
    "conversation-search.html": [/search-workbench/, /transcript/, /Selected context only/],
    "documents.html": [/ingestion-panel/, /scan-gates/, /Consent before transfer/],
  };
  Object.entries(focusedPages).forEach(([file, patterns]) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /focused-catalog-custody-workspaces\.css/);
    assert.match(html, /focused-governance-workspaces\.js/);
    patterns.forEach((pattern) => assert.match(html, pattern, `${file} is missing ${pattern}`));
  });
});

test("final focused batch completes core governance and evidence review surfaces", () => {
  const focusedPages = {
    "audit.html": [/audit-workbench/, /Two-phase evidence path/, /Immutable evidence/],
    "rules.html": [/rules-workbench/, /rule-lifecycle/, /Definitions are not pass results/],
    "ontology.html": [/ontology-release-strip/, /ontology-band-legend/, /Digest verified/],
    "blast-radius.html": [/impact-legend/, /impact-node is-gap/, /Relationship unavailable/],
    "rca.html": [/rc-evidence-status/, /Initiating change/, /Observing/],
  };
  Object.entries(focusedPages).forEach(([file, patterns]) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /focused-final-workspaces\.css/);
    patterns.forEach((pattern) => assert.match(html, pattern, `${file} is missing ${pattern}`));
  });
});

test("fifth focused batch exposes evolution, gaps, branches, conflicts, and priorities", () => {
  const focusedPages = {
    "context-selection-comparisons.html": [/Context policy evolution/, /state-legend/, /Version 8 candidate/],
    "conversation-search.html": [/search-mode-toggle/, /1 result unavailable/, /Source gap/],
    "rule-trace.html": [/trace-branches/, /If quality verification fails/, /Source recovery branch/],
    "scope.html": [/scope-conflict/, /Resolved boundary overlap/, /scope-history/],
    "forecast-learning.html": [/Forecast cohort comparison/, /Action required/, /calibration-quadrant/],
  };
  Object.entries(focusedPages).forEach(([file, patterns]) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /focused-decision-polish\.css/);
    patterns.forEach((pattern) => assert.match(html, pattern, `${file} is missing ${pattern}`));
  });
});

test("sixth focused batch clarifies operational result and fallback states", () => {
  const focusedPages = {
    "promotion.html": [/result-summary/, /Blocking gaps/, /gap-count/],
    "capabilities.html": [/representative declarations/, /Preview zero-result state/, /empty-preview/],
    "audit.html": [/append-boundary/, /Append next 25/, /Existing rows and ordering remain unchanged/],
    "reports.html": [/variable-contract/, /Partial render retained/, /3 of 4 widgets/],
    "rca.html": [/lookup-summary/, /Primary hypothesis/, /No response action recorded/],
  };
  Object.entries(focusedPages).forEach(([file, patterns]) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /focused-operational-polish\.css/);
    patterns.forEach((pattern) => assert.match(html, pattern, `${file} is missing ${pattern}`));
  });
});

test("Governance and Evidence workspaces prioritize work over dashboard chrome", () => {
  assert.match(governanceEvidenceStyles, /Compact non-dashboard framing/);
  assert.match(governanceEvidenceStyles, /\.fg-page > \.fg-boundary/);
  assert.match(governanceEvidenceStyles, /\.fg-page > \.fg-metrics/);
  assert.match(governanceEvidenceStyles, /\.compact-disclosure summary/);
  assert.match(governanceEvidenceStyles, /\.rca-page > \.rc-context/);
  assert.match(governanceEvidenceStyles, /grid-template-columns: repeat\(2, minmax\(0, 1fr\)\)/);

  governanceEvidenceMocks.forEach((file) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /governance-evidence-workspace\.css\?v=9/);
  });

  [
    "promotion.html",
    "context-selection-comparisons.html",
    "forecast-learning.html",
    "reports.html",
  ].forEach((file) => {
    assert.match(readFileSync(join(uiRoot, file), "utf8"), /<details class="compact-disclosure">/);
  });
  assert.match(readFileSync(join(uiRoot, "rca.html"), "utf8"), /class="cs-container cs-page rca-page"/);
});

test("every settings mock uses the production-aligned route surface", () => {
  settingsMocks.forEach((file) => {
    const html = readFileSync(join(uiRoot, file), "utf8");
    assert.match(html, /calm-slate\.css\?v=settings-route-v5/);
    assert.match(html, /calm-slate\.js\?v=settings-route-v5/);
    assert.doesNotMatch(html, /class="cs-btn/);
    if (/<(?:input|select|textarea)\b/.test(html)) {
      assert.match(html, /class="[^"]*cs-control-(?:input|select|textarea)/);
    }
  });
  assert.match(navigation, /var settingsPages = \[/);
  const settingsPagesBlock = navigation.slice(
    navigation.indexOf("var settingsPages ="),
    navigation.indexOf("function createSettingsSurface"),
  );
  assert.equal((settingsPagesBlock.match(/"settings(?:-[a-z]+)*\.html"/g) || []).length, 7);
  assert.match(navigation, /function createSettingsSurface\(\)/);
  assert.doesNotMatch(navigation, /function createSettingsWorkspace\(\)/);
  assert.doesNotMatch(sharedStyles, /\.cs-settings-workspace \{/);
  assert.match(sharedStyles, /\.cs-settings-surface \.cs-settings-content \{[\s\S]*max-width: 1080px/);
  assert.match(sharedStyles, /\.cs-settings-content > \.cs-settings-section:first-of-type/);
  assert.match(sharedStyles, /\.cs-settings-surface \.cs-settings-list \{\s*border-bottom: 0;/);
  assert.match(sharedStyles, /\.cs-settings-card-grid \{/);
  assert.match(sharedStyles, /@container \(max-width: 760px\) \{[\s\S]*\.cs-settings-surface \.cp-table td::before/);
  assert.match(sharedStyles, /\.cs-settings-surface \.cs-settings-content :where\([\s\S]*min-height: 44px/);
});
