import { useEffect, useMemo, useReducer, useRef, useState } from "preact/hooks";
import type { OperatorApiClient } from "../api";
import { loadConfig } from "../config";
import type { ConsoleDataMode } from "../console-data-mode";
import type { AgentOperationalActivityMessage } from "../agent-operational-activity";
import {
  agentStreamDescriptor,
  useAgentStream,
} from "../hooks/use-agent-stream";
import type { LiveStageEvent } from "../hooks/use-live-stream";
import { useLiveStream } from "../hooks/use-live-stream";
import { currentRoute, replaceRouteState, routeHref } from "../router";
import {
  liveSelectionState,
  makeInitialState,
  POOL_SIZE,
  reducer,
  type FilterKind,
} from "./live.model";
import {
  LivePanels,
  type LiveRouteUpdate,
  type LiveViewMode,
} from "./live.panels";
import {
  LIVE_OBSERVATION_LIMIT,
  mergeLiveObservations,
  type LiveObservationLoadState,
} from "./live.observations";
import { useLiveViewModel } from "./live.view-model";
import {
  OPERATIONS_SAMPLE_LIVE_EVENTS,
  OPERATIONS_SAMPLE_LIVE_EVENTS_PER_LOOP,
  OPERATIONS_SAMPLE_LIVE_HISTORY_COUNT,
  OPERATIONS_SAMPLE_LIVE_LOOP_INTERVAL_MS,
  OPERATIONS_SAMPLE_LIVE_STAGE_INTERVAL_MS,
  OPERATIONS_SAMPLE_LIVE_VISIBLE_COUNT,
  sampleLiveEvents,
} from "./operations.sample";

export { liveTraceHref } from "./live.ticker";

interface Props {
  readonly client: OperatorApiClient;
  readonly dataMode: ConsoleDataMode;
}

export const LIVE_BACKLOG_CAP = 1_000;
export const LIVE_FLUSH_CAP = 200;

export function appendLiveBacklog(
  backlog: readonly LiveStageEvent[],
  event: LiveStageEvent,
  cap = LIVE_BACKLOG_CAP,
): { readonly backlog: readonly LiveStageEvent[]; readonly dropped: number } {
  if (cap <= 0) return { backlog: [], dropped: 1 };
  const appended = [...backlog, event];
  const dropped = Math.max(0, appended.length - cap);
  return { backlog: dropped > 0 ? appended.slice(dropped) : appended, dropped };
}

export function drainLiveBacklog(
  backlog: readonly LiveStageEvent[],
  cap = LIVE_FLUSH_CAP,
): { readonly drained: readonly LiveStageEvent[]; readonly remaining: readonly LiveStageEvent[] } {
  const count = Math.max(0, cap);
  return { drained: backlog.slice(0, count), remaining: backlog.slice(count) };
}

export function LiveRoute({ client, dataMode }: Props) {
  const initialRoute = currentRoute();
  const [state, dispatch] = useReducer(
    reducer,
    undefined,
    () => makeInitialState(
      dataMode === "sample" ? OPERATIONS_SAMPLE_LIVE_VISIBLE_COUNT : POOL_SIZE,
    ),
  );
  const [tickerPaused, setTickerPaused] = useState(false);
  const [viewMode, setViewMode] = useState<LiveViewMode>(
    initialRoute.search.get("view") === "queue" ? "queue" : "flow",
  );
  const [frozenObserved, setFrozenObserved] = useState(0);
  const [droppedFrames, setDroppedFrames] = useState(0);
  const [observations, setObservations] = useState<
    readonly AgentOperationalActivityMessage[]
  >([]);
  const [observationLoadState, setObservationLoadState] =
    useState<LiveObservationLoadState>("loading");
  const [observationError, setObservationError] = useState<string | null>(null);
  const pausedRef = useRef(false);
  const frozenObservedRef = useRef(0);
  const pendingEventsRef = useRef<LiveStageEvent[]>([]);
  const pendingObservationsRef = useRef<AgentOperationalActivityMessage[]>([]);

  const updateRoute = ({
    eventId = state.selectedEventId,
    filter = state.filter,
    view = viewMode,
  }: LiveRouteUpdate): void => {
    dispatch({ kind: "filter", value: filter });
    setViewMode(view);
    replaceRouteState(routeHref("live", {
      params: {
        event: eventId,
        filter: filter === "all" ? null : filter,
        view: view === "flow" ? null : view,
        data: dataMode === "sample" ? "sample" : null,
      },
    }));
  };

  const selectEvent = (eventId: string | null): void => {
    dispatch({ kind: "select", event_id: eventId });
    replaceRouteState(routeHref("live", {
      params: {
        event: eventId,
        filter: state.filter === "all" ? null : state.filter,
        view: viewMode === "flow" ? null : viewMode,
        data: dataMode === "sample" ? "sample" : null,
      },
    }));
  };

  useEffect(() => {
    const sync = () => {
      const route = currentRoute();
      const filter = route.search.get("filter");
      dispatch({
        kind: "filter",
        value: filter === "hil" || filter === "deny" || filter === "failed" || filter === "stuck"
          ? filter
          : "all",
      });
      dispatch({ kind: "select", event_id: route.search.get("event") });
      setViewMode(route.search.get("view") === "queue" ? "queue" : "flow");
    };
    sync();
    window.addEventListener("popstate", sync);
    window.addEventListener("fdai:route-changed", sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener("fdai:route-changed", sync);
    };
  }, []);

  const url = useMemo(() => {
    const config = loadConfig();
    const base = config.operatorApiBaseUrl || (typeof window !== "undefined" ? window.location.origin : "");
    return `${base.replace(/\/$/, "")}/live/stream`;
  }, []);

  const stream = useLiveStream({
    url,
    enabled: dataMode === "live",
    getAuthorizationHeader: client.authorizationHeader,
    onEvent: (event) => {
      const next = appendLiveBacklog(pendingEventsRef.current, event);
      pendingEventsRef.current = [...next.backlog];
      if (next.dropped > 0) setDroppedFrames((current) => current + next.dropped);
      if (pausedRef.current) {
        frozenObservedRef.current += 1;
      }
    },
  });
  const status = dataMode === "sample" ? "open" : stream.status;
  const lastError = dataMode === "sample" ? null : stream.lastError;
  const streamSource = dataMode === "sample" ? "synthetic-dev" : stream.source;
  const observationDescriptor = useMemo(agentStreamDescriptor, []);
  const observationStream = useAgentStream({
    url: observationDescriptor.url,
    enabled: dataMode === "live",
    getAuthorizationHeader: client.authorizationHeader,
    onEvent: (event) => {
      if (event.type !== "agent.operational-activity") return;
      if (pausedRef.current) {
        pendingObservationsRef.current = [
          ...mergeLiveObservations(pendingObservationsRef.current, [event]),
        ];
        frozenObservedRef.current += 1;
        return;
      }
      setObservationLoadState("ready");
      setObservationError(null);
      setObservations((current) => mergeLiveObservations(current, [event]));
    },
  });

  useEffect(() => {
    if (dataMode !== "live") {
      setObservations([]);
      setObservationLoadState("unavailable");
      setObservationError(null);
      return undefined;
    }
    let cancelled = false;
    setObservationLoadState("loading");
    setObservationError(null);
    void client.listAgentActivity(LIVE_OBSERVATION_LIMIT)
      .then((page) => {
        if (cancelled) return;
        setObservations((current) => mergeLiveObservations(current, page.items));
        setObservationLoadState(
          page.source.includes("unavailable") ? "unavailable" : "ready",
        );
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setObservationLoadState("error");
        setObservationError(error instanceof Error ? error.message : String(error));
      });
    return () => {
      cancelled = true;
    };
  }, [client, dataMode]);

  useEffect(() => {
    if (dataMode !== "sample") return undefined;
    dispatch({ kind: "batch", events: OPERATIONS_SAMPLE_LIVE_EVENTS });
    dispatch({ kind: "seed-rate", now: Date.now(), per_tier_per_second: 1 });
    let nextEvent = OPERATIONS_SAMPLE_LIVE_HISTORY_COUNT;
    const stageHandles = new Set<number>();
    const enqueue = (event: LiveStageEvent) => {
      const next = appendLiveBacklog(pendingEventsRef.current, event);
      pendingEventsRef.current = [...next.backlog];
      if (next.dropped > 0) setDroppedFrames((current) => current + next.dropped);
      if (pausedRef.current) frozenObservedRef.current += 1;
    };
    const scheduleLoop = () => {
      for (let eventOffset = 0; eventOffset < OPERATIONS_SAMPLE_LIVE_EVENTS_PER_LOOP; eventOffset += 1) {
        const events = sampleLiveEvents(nextEvent + eventOffset, 1);
        events.forEach((event, stageIndex) => {
          const stageHandle = window.setTimeout(() => {
            stageHandles.delete(stageHandle);
            enqueue(event);
          }, eventOffset * 250 + stageIndex * OPERATIONS_SAMPLE_LIVE_STAGE_INTERVAL_MS);
          stageHandles.add(stageHandle);
        });
      }
      nextEvent += OPERATIONS_SAMPLE_LIVE_EVENTS_PER_LOOP;
    };
    scheduleLoop();
    const loopHandle = window.setInterval(
      scheduleLoop,
      OPERATIONS_SAMPLE_LIVE_LOOP_INTERVAL_MS,
    );
    return () => {
      window.clearInterval(loopHandle);
      stageHandles.forEach((handle) => window.clearTimeout(handle));
    };
  }, [dataMode]);

  useEffect(() => {
    const handle = window.setInterval(() => {
      if (pausedRef.current) {
        setFrozenObserved(frozenObservedRef.current);
        return;
      }
      const buffer = pendingEventsRef.current;
      if (buffer.length === 0) return;
      const { drained, remaining } = drainLiveBacklog(buffer);
      pendingEventsRef.current = [...remaining];
      dispatch({ kind: "batch", events: drained });
    }, 250);
    return () => {
      window.clearInterval(handle);
      pendingEventsRef.current = [];
    };
  }, []);

  useEffect(() => {
    const handle = window.setInterval(() => {
      if (pausedRef.current) return;
      dispatch({ kind: "tick", now: Date.now() });
    }, 250);
    return () => window.clearInterval(handle);
  }, []);

  const togglePause = () => {
    if (tickerPaused) {
      pausedRef.current = false;
      setObservations((current) =>
        mergeLiveObservations(current, pendingObservationsRef.current));
      pendingObservationsRef.current = [];
      setTickerPaused(false);
    } else {
      pausedRef.current = true;
      frozenObservedRef.current = 0;
      setFrozenObserved(0);
      setTickerPaused(true);
    }
  };

  const selectedTile = state.selectedEventId
    ? state.tiles.find((tile) => tile?.event_id === state.selectedEventId) ?? null
    : null;
  const selectionState = liveSelectionState(
    state.selectedEventId,
    selectedTile,
    state.session_total,
  );
  const view = useLiveViewModel(
    state,
    status,
    streamSource,
    selectedTile,
    droppedFrames,
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      const tag = target?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || target?.isContentEditable) return;
      if (target?.closest('[role="dialog"]')) return;
      if (event.key === "Escape" && state.selectedEventId) {
        selectEvent(null);
        event.preventDefault();
        return;
      }
      if (event.key === "p" || event.key === "P") {
        togglePause();
        event.preventDefault();
        return;
      }
      const index = ["1", "2", "3", "4", "5"].indexOf(event.key);
      if (index >= 0) {
        const filters: readonly FilterKind[] = ["all", "hil", "deny", "failed", "stuck"];
        const value = filters[index];
        if (value !== undefined) {
          updateRoute({ filter: value });
          event.preventDefault();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [state.selectedEventId, state.filter, tickerPaused, state.session_total, viewMode]);

  return (
    <LivePanels
      state={state}
      view={view}
      status={status}
      lastError={lastError}
      streamSource={streamSource}
      tickerPaused={tickerPaused}
      frozenObserved={frozenObserved}
      droppedFrames={droppedFrames}
      observations={observations}
      observationLoadState={observationLoadState}
      observationStreamStatus={observationStream.status}
      observationStreamSource={observationStream.source}
      observationError={observationError}
      viewMode={viewMode}
      selectionState={selectionState}
      selectedTile={selectedTile}
      togglePause={togglePause}
      updateRoute={updateRoute}
      selectEvent={selectEvent}
    />
  );
}
