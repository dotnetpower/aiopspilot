import type {
  AgentOperationalActivityMessage,
} from "../agent-operational-activity";
import type { AgentStreamStatus } from "../hooks/use-agent-stream";
import {
  observationSourceLabel,
  type ObservationSource,
} from "../hooks/observation-source";
import { t as appT } from "../i18n";
import { routeHref } from "../router";
import { formatConsoleTime } from "../time-format";
import { t } from "./i18n/live";

export const LIVE_OBSERVATION_LIMIT = 24;
const LIVE_OBSERVATION_VISIBLE_COUNT = 8;

export type LiveObservationLoadState = "loading" | "ready" | "unavailable" | "error";
export type LiveObservationPresentation =
  | "loading"
  | "items"
  | "waiting"
  | "unavailable"
  | "error"
  | "empty";

export function liveObservationPresentation(
  loadState: LiveObservationLoadState,
  streamStatus: AgentStreamStatus,
  itemCount: number,
): LiveObservationPresentation {
  if (itemCount > 0) return "items";
  if (loadState === "loading") return "loading";
  if (loadState === "error") return "error";
  if (loadState === "unavailable") {
    return streamStatus === "open" ? "waiting" : "unavailable";
  }
  return "empty";
}

export function mergeLiveObservations(
  current: readonly AgentOperationalActivityMessage[],
  incoming: readonly AgentOperationalActivityMessage[],
  limit = LIVE_OBSERVATION_LIMIT,
): readonly AgentOperationalActivityMessage[] {
  if (!Number.isInteger(limit) || limit < 1) {
    throw new Error("Live observation limit MUST be a positive integer");
  }
  const activityKey = (item: AgentOperationalActivityMessage) =>
    item.correlation_id
      ? `${item.kind}:${item.observation_domain ?? "none"}:${item.correlation_id}`
      : item.activity_id;
  const byActivity = new Map(current.map((item) => [activityKey(item), item]));
  incoming.forEach((item) => {
    const key = activityKey(item);
    const previous = byActivity.get(key);
    if (!previous || Date.parse(item.observed_at) >= Date.parse(previous.observed_at)) {
      byActivity.set(key, item);
    }
  });
  return [...byActivity.values()]
    .sort((left, right) => Date.parse(right.observed_at) - Date.parse(left.observed_at))
    .slice(0, limit);
}

function activityLabel(item: AgentOperationalActivityMessage): string {
  if (item.observation_domain) {
    return appT(`agentActivity.observationDomain.${item.observation_domain}`);
  }
  return appT(`agentActivity.log.lane.${item.kind}`);
}

function activityHref(item: AgentOperationalActivityMessage): string {
  return routeHref("agent-activity", {
    params: { q: item.observation_domain ?? item.kind },
  });
}

export function LiveObservations({
  items,
  loadState,
  streamStatus,
  streamSource,
  error,
}: {
  readonly items: readonly AgentOperationalActivityMessage[];
  readonly loadState: LiveObservationLoadState;
  readonly streamStatus: AgentStreamStatus;
  readonly streamSource: ObservationSource;
  readonly error: string | null;
}) {
  const visible = items.slice(0, LIVE_OBSERVATION_VISIBLE_COUNT);
  const active = items.filter((item) => item.status === "started").length;
  const degraded = items.filter(
    (item) => item.status === "degraded" || item.status === "failed",
  ).length;
  const presentation = liveObservationPresentation(
    loadState,
    streamStatus,
    visible.length,
  );

  return (
    <section class="live-observations" aria-labelledby="live-observations-title">
      <header>
        <div>
          <span class="live-eyebrow">{t("live.observations.eyebrow")}</span>
          <h3 id="live-observations-title">{t("live.observations.title")}</h3>
        </div>
        <div class="live-observations-summary">
          <span>{t("live.observations.active", { count: active })}</span>
          <span>{t("live.observations.degraded", { count: degraded })}</span>
          <span>
            {streamStatus === "open"
              ? observationSourceLabel(streamSource)
              : t(`live.status.${streamStatus}`)}
          </span>
          <a href={routeHref("agent-activity")}>{t("live.observations.openActivity")}</a>
        </div>
      </header>
      <p>{t("live.observations.note")}</p>
      {presentation === "loading" ? (
        <div class="live-observation-grid" role="status" aria-busy="true">
          <span class="sr-only">{t("live.observations.loading")}</span>
          {Array.from({ length: 4 }, (_, index) => (
            <span key={index} class="live-observation-skeleton skeleton-shimmer" aria-hidden="true" />
          ))}
        </div>
      ) : presentation === "error" ? (
        <div class="live-observation-state is-error" role="alert">
          {t("live.observations.error", { error: error ?? t("live.control.notObserved") })}
        </div>
      ) : presentation === "waiting" ? (
        <div class="live-observation-state" role="status">
          {t("live.observations.waiting")}
        </div>
      ) : presentation === "unavailable" ? (
        <div class="live-observation-state" role="status">
          {t("live.observations.unavailable")}
        </div>
      ) : presentation === "empty" ? (
        <div class="live-observation-state" role="status">
          {t("live.observations.empty")}
        </div>
      ) : (
        <div class="live-observation-grid">
          {visible.map((item) => (
            <a
              key={item.activity_id}
              class="live-observation-item"
              data-status={item.status}
              href={activityHref(item)}
            >
              <span class="live-observation-topline">
                <strong>{activityLabel(item)}</strong>
                <span class={`live-observation-status is-${item.status}`}>
                  {t(`live.observations.status.${item.status}`)}
                </span>
              </span>
              <span class="live-observation-detail">
                {item.owner_agent} · {t("live.observations.evidence", { count: item.evidence_count })}
              </span>
              <span class="live-observation-meta">
                <time dateTime={item.observed_at}>{formatConsoleTime(item.observed_at)}</time>
                <span>{t(`live.observations.freshness.${item.freshness}`)}</span>
              </span>
            </a>
          ))}
        </div>
      )}
    </section>
  );
}
