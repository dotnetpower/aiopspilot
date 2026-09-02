import { useEffect, useState } from "preact/hooks";
import { isOptionalOperatorApiUnavailable, OperatorApiError } from "../api";
import type { OperatorApiClient } from "../api";
import {
  AsyncBoundary,
  DataTable,
  KpiCard,
  KpiGrid,
  PageHeader,
  StatusPill,
  type AsyncState,
  type Column,
} from "../components/ui";
import { usePublishViewContext, type ViewSnapshot } from "../deck/context";
import { composeGlossary } from "../deck/glossary";
import { t } from "../i18n";
import { currentRoute, routeHref } from "../router";
import { formatConsoleTimestamp } from "../time-format";
import {
  panelArray,
  panelBoolean,
  panelNonEmptyString,
  panelNonNegativeInteger,
  panelNullableString,
  panelRecord,
  panelStringArray,
} from "./panel-decode";

const SEVERITIES = ["low", "medium", "high", "critical"] as const;
type Severity = (typeof SEVERITIES)[number];
const VERDICTS = ["clear", "needs_review", "blocked"] as const;
type Verdict = (typeof VERDICTS)[number];
const MODES = ["shadow", "enforce"] as const;
type TwinMode = (typeof MODES)[number];
const FRESHNESS_STATES = ["fresh", "stale", "unavailable", "unknown"] as const;
type Freshness = (typeof FRESHNESS_STATES)[number];

export interface AssuranceTwinFinding {
  readonly rule_id: string;
  readonly resource_type: string;
  readonly resource_ref: string;
  readonly severity: Severity;
  readonly reason: string;
  readonly evidence_refs: readonly string[];
}

export interface AssuranceTwinPostureReport {
  readonly scope: string;
  readonly generated_at: string;
  readonly mode: TwinMode;
  readonly verdict: Verdict;
  readonly blocks_action: boolean;
  readonly resource_count: number;
  readonly rule_count: number;
  readonly highest_severity: Severity | null;
  readonly severity_counts: Readonly<Record<Severity, number>>;
  readonly finding_count: number;
  readonly findings: readonly AssuranceTwinFinding[];
  readonly freshness: Freshness;
  readonly reason_codes: readonly string[];
}

export interface AssuranceTwinReviewSummary {
  readonly review_key: string;
  readonly pr_ref: string;
  readonly generated_at: string;
  readonly mode: TwinMode;
  readonly verdict: Verdict;
  readonly finding_count: number;
  readonly freshness: Freshness;
  readonly reason_codes: readonly string[];
}

export interface AssuranceTwinReviewDetail extends AssuranceTwinReviewSummary {
  readonly findings: readonly AssuranceTwinFinding[];
}

export interface AssuranceTwinResponse {
  readonly posture: {
    readonly available: boolean;
    readonly reports: readonly AssuranceTwinPostureReport[];
  };
  readonly reviews: {
    readonly available: boolean;
    readonly reviews: readonly AssuranceTwinReviewSummary[];
  };
}

export function buildAssuranceTwinViewSnapshot(data: AssuranceTwinResponse): ViewSnapshot {
  const report = data.posture.reports[0] ?? null;
  return {
    routeId: "assurance-twin",
    routeLabel: t("route.assuranceTwin"),
    purpose: t("assuranceTwin.readOnlyBody"),
    glossary: composeGlossary([], [
      {
        term: t("route.assuranceTwin"),
        plain: t("assuranceTwin.subtitle"),
        tech: "PostureAssessmentReport",
      },
    ]),
    headline: report
      ? `${t("assuranceTwin.verdict")}: ${t(`assuranceTwin.verdict.${report.verdict}`)}; `
        + `${t("assuranceTwin.reviews")}: ${data.reviews.reviews.length}`
      : t("assuranceTwin.unavailable"),
    capturedAt: new Date().toISOString(),
    facts: report
      ? [
        { key: "verdict", label: t("assuranceTwin.verdict"), value: report.verdict },
        { key: "resource_count", label: t("assuranceTwin.resourceCount"), value: report.resource_count },
        { key: "rule_count", label: t("assuranceTwin.ruleCount"), value: report.rule_count },
      ]
      : [],
    records: {
      reviews: data.reviews.reviews.map((row) => ({
        review_key: row.review_key,
        pr_ref: row.pr_ref,
        verdict: row.verdict,
        finding_count: row.finding_count,
        generated_at: row.generated_at,
      })),
    },
  };
}

const POSTURE_ROOT_KEYS = new Set(["surface", "available", "source", "reports"]);
const REPORT_KEYS = new Set([
  "scope",
  "generated_at",
  "mode",
  "verdict",
  "blocks_action",
  "resource_count",
  "rule_count",
  "highest_severity",
  "severity_counts",
  "finding_count",
  "findings",
  "freshness",
  "reason_codes",
]);
const REVIEWS_ROOT_KEYS = new Set(["surface", "available", "source", "reviews"]);
const REVIEW_SUMMARY_KEYS = new Set([
  "review_key",
  "pr_ref",
  "generated_at",
  "mode",
  "verdict",
  "finding_count",
  "freshness",
  "reason_codes",
]);
const FINDING_KEYS = new Set([
  "rule_id",
  "resource_type",
  "resource_ref",
  "severity",
  "reason",
  "evidence_refs",
]);

export function AssuranceTwinRoute({ client }: { readonly client: OperatorApiClient }) {
  const reviewId = currentRoute().segments[0] ?? null;
  const [state, setState] = useState<AsyncState<AssuranceTwinResponse>>({ status: "loading" });
  const [detailState, setDetailState] = useState<AsyncState<AssuranceTwinReviewDetail> | null>(null);

  useEffect(() => {
    let cancelled = false;
    void loadAssuranceTwinState(client).then((next) => {
      if (!cancelled) setState(next);
    });
    return () => { cancelled = true; };
  }, [client]);

  useEffect(() => {
    if (reviewId === null) {
      setDetailState(null);
      return;
    }
    let cancelled = false;
    setDetailState({ status: "loading" });
    void loadAssuranceTwinReviewDetail(client, reviewId).then((next) => {
      if (!cancelled) setDetailState(next);
    });
    return () => { cancelled = true; };
  }, [client, reviewId]);

  return (
    <div class="stack evidence-route">
      <PageHeader title={t("route.assuranceTwin")} subtitle={t("assuranceTwin.subtitle")} />
      {reviewId === null
        ? (
          <AsyncBoundary state={state} resourceLabel={t("assuranceTwin.resourceLabel")}>
            {(data) => <AssuranceTwinBody data={data} />}
          </AsyncBoundary>
        )
        : (
          <AsyncBoundary
            state={detailState ?? { status: "loading" }}
            resourceLabel={t("assuranceTwin.reviewDetailResourceLabel")}
          >
            {(detail) => <AssuranceTwinReviewDetailBody detail={detail} />}
          </AsyncBoundary>
        )}
    </div>
  );
}

export async function loadAssuranceTwinState(
  client: Pick<OperatorApiClient, "panel">,
): Promise<AsyncState<AssuranceTwinResponse>> {
  try {
    const [posture, reviews] = await Promise.all([
      client.panel<unknown>("/assurance-twin/posture"),
      client.panel<unknown>("/assurance-twin/reviews"),
    ]);
    return {
      status: "ready",
      data: {
        posture: decodeAssuranceTwinPosture(posture),
        reviews: decodeAssuranceTwinReviews(reviews),
      },
    };
  } catch (error) {
    if (isOptionalOperatorApiUnavailable(error)) {
      return { status: "unavailable", message: t("assuranceTwin.unavailable") };
    }
    return { status: "error", message: error instanceof Error ? error.message : String(error) };
  }
}

export async function loadAssuranceTwinReviewDetail(
  client: Pick<OperatorApiClient, "panel">,
  reviewId: string,
): Promise<AsyncState<AssuranceTwinReviewDetail>> {
  try {
    const payload = await client.panel<unknown>(
      `/assurance-twin/reviews/${encodeURIComponent(reviewId)}`,
    );
    return { status: "ready", data: decodeAssuranceTwinReviewDetail(payload) };
  } catch (error) {
    if (isOptionalOperatorApiUnavailable(error)) {
      return { status: "unavailable", message: t("assuranceTwin.unavailable") };
    }
    return { status: "error", message: error instanceof Error ? error.message : String(error) };
  }
}

function decodeAssuranceTwinPosture(value: unknown): AssuranceTwinResponse["posture"] {
  const root = panelRecord(value, "assurance twin posture");
  requireExactKeys(root, POSTURE_ROOT_KEYS, "assurance twin posture");
  const available = panelBoolean(root, "available", "assurance twin posture");
  const rawReports = panelArray(root["reports"], "assurance twin posture.reports");
  const reports = rawReports.map((item, index) => decodeReport(item, index));
  return { available, reports };
}

function decodeAssuranceTwinReviews(value: unknown): AssuranceTwinResponse["reviews"] {
  const root = panelRecord(value, "assurance twin reviews");
  requireExactKeys(root, REVIEWS_ROOT_KEYS, "assurance twin reviews");
  const available = panelBoolean(root, "available", "assurance twin reviews");
  const rawReviews = panelArray(root["reviews"], "assurance twin reviews.reviews");
  const reviews = rawReviews.map((item, index) => decodeReviewSummary(item, index));
  return { available, reviews };
}

function decodeAssuranceTwinReviewDetail(value: unknown): AssuranceTwinReviewDetail {
  const root = panelRecord(value, "assurance twin review detail");
  const summary = decodeReviewSummary(root, 0);
  const rawFindings = panelArray(root["findings"], "assurance twin review detail.findings");
  const findings = rawFindings.map((item, index) => decodeFinding(item, index));
  return { ...summary, findings };
}

function decodeReport(value: unknown, index: number): AssuranceTwinPostureReport {
  const row = panelRecord(value, `assurance twin posture.reports[${index}]`);
  requireExactKeys(row, REPORT_KEYS, `assurance twin posture.reports[${index}]`);
  const rawFindings = panelArray(row["findings"], "assurance twin posture report.findings");
  const findings = rawFindings.map((item, i) => decodeFinding(item, i));
  const findingCount = panelNonNegativeInteger(row, "finding_count", "assurance twin posture report");
  if (findingCount !== findings.length) {
    throw new OperatorApiError(502, "invalid Operator API response: assurance twin finding_count MUST match findings");
  }
  return {
    scope: panelNonEmptyString(row, "scope", "assurance twin posture report"),
    generated_at: panelNonEmptyString(row, "generated_at", "assurance twin posture report"),
    mode: enumValue(row, "mode", MODES, "assurance twin posture report"),
    verdict: enumValue(row, "verdict", VERDICTS, "assurance twin posture report"),
    blocks_action: panelBoolean(row, "blocks_action", "assurance twin posture report"),
    resource_count: panelNonNegativeInteger(row, "resource_count", "assurance twin posture report"),
    rule_count: panelNonNegativeInteger(row, "rule_count", "assurance twin posture report"),
    highest_severity: nullableEnum(row, "highest_severity", SEVERITIES, "assurance twin posture report"),
    severity_counts: severityCounts(row["severity_counts"]),
    finding_count: findingCount,
    findings,
    freshness: enumValue(row, "freshness", FRESHNESS_STATES, "assurance twin posture report"),
    reason_codes: panelStringArray(row["reason_codes"], "assurance twin posture report.reason_codes"),
  };
}

function decodeReviewSummary(value: unknown, index: number): AssuranceTwinReviewSummary {
  const row = panelRecord(value, `assurance twin reviews[${index}]`);
  return {
    review_key: panelNonEmptyString(row, "review_key", "assurance twin review"),
    pr_ref: panelNonEmptyString(row, "pr_ref", "assurance twin review"),
    generated_at: panelNonEmptyString(row, "generated_at", "assurance twin review"),
    mode: enumValue(row, "mode", MODES, "assurance twin review"),
    verdict: enumValue(row, "verdict", VERDICTS, "assurance twin review"),
    finding_count: panelNonNegativeInteger(row, "finding_count", "assurance twin review"),
    freshness: enumValue(row, "freshness", FRESHNESS_STATES, "assurance twin review"),
    reason_codes: panelStringArray(row["reason_codes"], "assurance twin review.reason_codes"),
  };
}

function decodeFinding(value: unknown, index: number): AssuranceTwinFinding {
  const row = panelRecord(value, `assurance twin finding[${index}]`);
  requireExactKeys(row, FINDING_KEYS, `assurance twin finding[${index}]`);
  return {
    rule_id: panelNonEmptyString(row, "rule_id", "assurance twin finding"),
    resource_type: panelNonEmptyString(row, "resource_type", "assurance twin finding"),
    resource_ref: panelNonEmptyString(row, "resource_ref", "assurance twin finding"),
    severity: enumValue(row, "severity", SEVERITIES, "assurance twin finding"),
    reason: panelNonEmptyString(row, "reason", "assurance twin finding"),
    evidence_refs: panelStringArray(row["evidence_refs"], "assurance twin finding.evidence_refs"),
  };
}

function severityCounts(value: unknown): Readonly<Record<Severity, number>> {
  const row = panelRecord(value, "assurance twin severity_counts");
  const counts = {} as Record<Severity, number>;
  for (const severity of SEVERITIES) {
    counts[severity] = panelNonNegativeInteger(row, severity, "assurance twin severity_counts");
  }
  return counts;
}

function enumValue<T extends string>(
  row: Readonly<Record<string, unknown>>,
  key: string,
  allowed: readonly T[],
  label: string,
): T {
  const raw = panelNonEmptyString(row, key, label);
  if (!(allowed as readonly string[]).includes(raw)) {
    throw new OperatorApiError(502, `invalid Operator API response: ${label}.${key} is invalid`);
  }
  return raw as T;
}

function nullableEnum<T extends string>(
  row: Readonly<Record<string, unknown>>,
  key: string,
  allowed: readonly T[],
  label: string,
): T | null {
  const raw = panelNullableString(row, key, label);
  if (raw === null) return null;
  if (!(allowed as readonly string[]).includes(raw)) {
    throw new OperatorApiError(502, `invalid Operator API response: ${label}.${key} is invalid`);
  }
  return raw as T;
}

function requireExactKeys(
  value: Readonly<Record<string, unknown>>,
  allowed: ReadonlySet<string>,
  label: string,
): void {
  const unsupported = Object.keys(value).find((key) => !allowed.has(key));
  if (unsupported) {
    throw new OperatorApiError(502, `invalid Operator API response: ${label}.${unsupported} is not allowed`);
  }
}

function verdictTone(verdict: Verdict): "positive" | "warning" | "danger" {
  if (verdict === "clear") return "positive";
  if (verdict === "needs_review") return "warning";
  return "danger";
}

function verdictStatusKind(verdict: Verdict): "success" | "warning" | "danger" {
  if (verdict === "clear") return "success";
  if (verdict === "needs_review") return "warning";
  return "danger";
}

function freshnessStatusKind(freshness: Freshness): "success" | "warning" | "danger" | "neutral" {
  if (freshness === "fresh") return "success";
  if (freshness === "stale") return "warning";
  if (freshness === "unavailable") return "danger";
  return "neutral";
}

function EvidenceGaps({ reasonCodes }: { readonly reasonCodes: readonly string[] }) {
  if (reasonCodes.length === 0) return null;
  return (
    <div class="assurance-twin-gaps">
      <strong>{t("assuranceTwin.evidenceGaps")}</strong>
      <ul>
        {reasonCodes.map((code) => (
          <li key={code}><span class="mono">{code}</span></li>
        ))}
      </ul>
    </div>
  );
}

function AssuranceTwinBody({ data }: { readonly data: AssuranceTwinResponse }) {
  usePublishViewContext(() => buildAssuranceTwinViewSnapshot(data), [data]);
  const report = data.posture.reports[0] ?? null;
  const reviewsHref = `${routeHref("assurance-twin")}#assurance-twin-reviews`;
  const columns: readonly Column<AssuranceTwinReviewSummary>[] = [
    {
      key: "pr_ref",
      header: t("assuranceTwin.column.change"),
      render: (row) => (
        <a class="mono" href={routeHref("assurance-twin", { segments: [row.review_key] })}>
          {row.pr_ref}
        </a>
      ),
    },
    {
      key: "verdict",
      header: t("assuranceTwin.column.verdict"),
      render: (row) => (
        <StatusPill
          kind={verdictStatusKind(row.verdict)}
          label={t(`assuranceTwin.verdict.${row.verdict}`)}
        />
      ),
    },
    {
      key: "mode",
      header: t("assuranceTwin.column.mode"),
      render: (row) => <StatusPill kind={row.mode === "enforce" ? "enforce" : "shadow"} label={t(`assuranceTwin.mode.${row.mode}`)} />,
    },
    {
      key: "findings",
      header: t("assuranceTwin.column.findings"),
      render: (row) => row.finding_count,
    },
    {
      key: "freshness",
      header: t("assuranceTwin.column.freshness"),
      render: (row) => (
        <StatusPill
          kind={freshnessStatusKind(row.freshness)}
          label={t(`assuranceTwin.freshness.${row.freshness}`)}
        />
      ),
    },
    {
      key: "generated_at",
      header: t("assuranceTwin.column.generatedAt"),
      render: (row) => formatConsoleTimestamp(row.generated_at),
    },
  ];
  return (
    <div class="stack">
      <div class="governance-readonly-banner">
        <strong>{t("assuranceTwin.readOnlyTitle")}</strong>
        <span>{t("assuranceTwin.readOnlyBody")}</span>
      </div>
      {report
        ? (
          <>
            <KpiGrid>
              <KpiCard
                href={reviewsHref}
                label={t("assuranceTwin.verdict")}
                value={t(`assuranceTwin.verdict.${report.verdict}`)}
                tone={verdictTone(report.verdict)}
              />
              <KpiCard href={reviewsHref} label={t("assuranceTwin.resourceCount")} value={report.resource_count} />
              <KpiCard href={reviewsHref} label={t("assuranceTwin.ruleCount")} value={report.rule_count} />
              <KpiCard
                href={reviewsHref}
                label={t("assuranceTwin.highestSeverity")}
                value={report.highest_severity ? t(`assuranceTwin.severity.${report.highest_severity}`) : t("assuranceTwin.noFindings")}
                tone={report.highest_severity === "critical" || report.highest_severity === "high" ? "danger" : "default"}
              />
              <KpiCard
                href={reviewsHref}
                label={t("assuranceTwin.freshness")}
                value={t(`assuranceTwin.freshness.${report.freshness}`)}
                evidenceState={report.freshness === "unavailable" ? "not-connected" : "measured"}
                tone={report.freshness === "unavailable" ? "danger" : "default"}
              />
            </KpiGrid>
            <EvidenceGaps reasonCodes={report.reason_codes} />
          </>
        )
        : <div class="muted">{t("assuranceTwin.noPostureReport")}</div>}
      <div id="assurance-twin-reviews">
        <h2>{t("assuranceTwin.reviews")}</h2>
        <DataTable
          columns={columns}
          rows={data.reviews.reviews}
          keyOf={(row) => row.review_key}
          empty={t("assuranceTwin.reviewsEmpty")}
        />
      </div>
    </div>
  );
}

function AssuranceTwinReviewDetailBody({ detail }: { readonly detail: AssuranceTwinReviewDetail }) {
  const columns: readonly Column<AssuranceTwinFinding>[] = [
    { key: "rule", header: t("assuranceTwin.column.rule"), render: (row) => <span class="mono">{row.rule_id}</span> },
    { key: "resource", header: t("assuranceTwin.column.resource"), render: (row) => `${row.resource_type} / ${row.resource_ref}` },
    {
      key: "severity",
      header: t("assuranceTwin.column.severity"),
      render: (row) => <StatusPill kind={row.severity === "critical" || row.severity === "high" ? "danger" : "warning"} label={t(`assuranceTwin.severity.${row.severity}`)} />,
    },
    { key: "reason", header: t("assuranceTwin.column.reason"), render: (row) => row.reason },
  ];
  return (
    <div class="stack">
      <a href={routeHref("assurance-twin")}>{t("assuranceTwin.backToReviews")}</a>
      <KpiGrid>
        <KpiCard
          href={routeHref("assurance-twin", { segments: [detail.review_key] })}
          label={t("assuranceTwin.verdict")}
          value={t(`assuranceTwin.verdict.${detail.verdict}`)}
          tone={verdictTone(detail.verdict)}
        />
        <KpiCard
          href={routeHref("assurance-twin", { segments: [detail.review_key] })}
          label={t("assuranceTwin.column.findings")}
          value={detail.finding_count}
        />
      </KpiGrid>
      <EvidenceGaps reasonCodes={detail.reason_codes} />
      <DataTable
        columns={columns}
        rows={detail.findings}
        keyOf={(row, index) => `${row.rule_id}:${row.resource_ref}:${index}`}
        empty={t("assuranceTwin.reviewsEmpty")}
      />
    </div>
  );
}
