import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../", import.meta.url);

async function loadEnKo() {
  const [english, korean] = await Promise.all([
    readFile(
      new URL(
        "../docs/roadmap/interfaces/channels-and-notifications.md",
        root,
      ),
      "utf8",
    ),
    readFile(
      new URL(
        "../docs/roadmap/interfaces/channels-and-notifications-ko.md",
        root,
      ),
      "utf8",
    ),
  ]);
  return { english, korean };
}

async function loadDiagramSource(id) {
  return readFile(new URL(`../docs/diagrams/${id}.diagram.yaml`, root), "utf8");
}

async function loadManifest(id) {
  const source = await readFile(
    new URL(`public/diagrams/generated/${id}.manifest.json`, root),
    "utf8",
  );
  return JSON.parse(source);
}

test("channels-and-notifications page embeds its diagram with matching manifest alt text", async () => {
  const { english, korean } = await loadEnKo();
  const id = "fdai-channels-and-notifications-01";
  const manifest = await loadManifest(id);
  const enAltMatch = english.match(
    new RegExp(`!\\[([^\\]]+)\\]\\([^\\n)]*${id}\\.en\\.svg\\)`, "u"),
  );
  const koAltMatch = korean.match(
    new RegExp(`!\\[([^\\]]+)\\]\\([^\\n)]*${id}\\.ko\\.svg\\)`, "u"),
  );
  assert.ok(enAltMatch, `expected an English markdown embed for ${id}`);
  assert.ok(koAltMatch, `expected a Korean markdown embed for ${id}`);
  assert.equal(enAltMatch[1], manifest.locales.en.alt);
  assert.equal(koAltMatch[1], manifest.locales.ko.alt);
});

test("Round 15 regression: diagram source translates adapter/interface node labels and the edge label into Korean", async () => {
  const source = await loadDiagramSource("fdai-channels-and-notifications-01");
  for (const untranslated of [
    "ko: Channel interface",
    "ko: teams adapter",
    "ko: slack adapter",
    "ko: email adapter",
    "ko: webhook adapter",
    "ko: pager adapter",
    "ko: category-tagged / message",
  ]) {
    assert.ok(
      !source.includes(untranslated),
      `diagram must not leave "${untranslated}" byte-identical to English`,
    );
  }
  assert.ok(source.includes("ko: 채널 인터페이스"));
  assert.ok(source.includes("ko: teams 어댑터"));
  assert.ok(source.includes("ko: slack 어댑터"));
  assert.ok(source.includes("ko: email 어댑터"));
  assert.ok(source.includes("ko: webhook 어댑터"));
  assert.ok(source.includes("ko: pager 어댑터"));
  assert.ok(source.includes("ko: 카테고리 태그 / 메시지"));
  // Module-identifier-style labels stay English by established repo convention.
  for (const kept of ["risk-gate", "channel-router", "observability", "digest-writer", "fdai-api"]) {
    assert.ok(source.includes(`en: ${kept}`));
    assert.ok(source.includes(`ko: ${kept}`));
  }
});

test("Round 15 regression: fictional Teams auth class names and env vars are replaced with real ones", async () => {
  const { english, korean } = await loadEnKo();
  for (const stale of [
    "BotFrameworkJwtAuthenticator",
    "TeamsPrincipalResolver",
    "FDAI_TEAMS_BOT_APP_ID",
    "FDAI_TEAMS_PRINCIPAL_BINDINGS_JSON",
  ]) {
    assert.ok(!english.includes(stale), `English page must not re-introduce "${stale}"`);
    assert.ok(!korean.includes(stale), `Korean page must not re-introduce "${stale}"`);
  }
  assert.ok(english.includes("TeamsServiceTokenVerifier"));
  assert.ok(english.includes("ChannelPrincipalResolver"));
  assert.ok(english.includes("FDAI_TEAMS_APPLICATION_ID"));
  assert.ok(english.includes("FDAI_TEAMS_PRINCIPAL_MAP_JSON"));
  assert.ok(korean.includes("TeamsServiceTokenVerifier"));
  assert.ok(korean.includes("ChannelPrincipalResolver"));
  assert.ok(korean.includes("FDAI_TEAMS_APPLICATION_ID"));
  assert.ok(korean.includes("FDAI_TEAMS_PRINCIPAL_MAP_JSON"));
});

test("Round 15 regression: fictional HIL-decision-recovery env vars are replaced with a truthful dataclass-default description", async () => {
  const { english, korean } = await loadEnKo();
  for (const stale of [
    "FDAI_HIL_DECISION_RECOVERY_INTERVAL_SECONDS",
    "FDAI_HIL_DECISION_PUBLISH_TIMEOUT_SECONDS",
    "FDAI_HIL_DECISION_MAX_DELIVERY_ATTEMPTS",
  ]) {
    assert.ok(!english.includes(stale), `English page must not re-introduce "${stale}"`);
    assert.ok(!korean.includes(stale), `Korean page must not re-introduce "${stale}"`);
  }
  assert.ok(english.includes("HilDecisionRecoveryConfig"));
  assert.ok(korean.includes("HilDecisionRecoveryConfig"));
});

test("Round 15 regression: role-dm/mention-artifact-owner audience modes are described as declared design, not enforced", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(english.includes("declared design, not yet enforced"));
  assert.ok(korean.includes("선언된 설계일 뿐, 아직 시행되지 않습니다"));
  assert.ok(korean.includes("선언된 설계; matrix 로더에서 아직 시행되지 않음"));
});

test("Round 15 regression: broken anchors are fixed to their real Korean heading slugs", async () => {
  const { english, korean } = await loadEnKo();
  assert.ok(!english.includes("#hil-approval-integrity"));
  assert.ok(english.includes("#human-approval-integrity"));
  for (const staleAnchor of [
    "#hil-approval-integrity",
    "#105-guest-entra-b2b-users",
    "#42-security-groups-slots",
    "#104-chatops-teams-sign-in",
    "#rate-limiting-and-kill-switch-dos-and-containment",
  ]) {
    assert.ok(
      !korean.includes(staleAnchor),
      `Korean page must not re-introduce the broken anchor "${staleAnchor}"`,
    );
  }
  assert.ok(korean.includes("#사람-승인-무결성"));
  assert.ok(korean.includes("#105-게스트-entra-b2b-사용자"));
  assert.ok(korean.includes("#42-보안-그룹-slots"));
  assert.ok(korean.includes("#104-chatops-teams-사인인"));
  assert.ok(korean.includes("#비율-limiting과-비상-정지-dos와-억제"));
});

test("Round 15 regression: duplicated-syllable typo and space-detached particles are fixed", async () => {
  const { korean } = await loadEnKo();
  assert.ok(!korean.includes("인증된된"));
  assert.ok(korean.includes("인증된 ChatOps"));
  for (const broken of [
    "구간 에",
    "작성기 는",
    "호출자 가",
    "전송 를",
    "본문 와",
    "라우터 에",
    "전달 하지",
    "구간 는",
  ]) {
    assert.ok(
      !korean.includes(broken),
      `Korean page must not re-introduce the broken particle usage "${broken}"`,
    );
  }
});
