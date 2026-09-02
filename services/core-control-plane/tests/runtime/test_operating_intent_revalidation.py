"""Bounded revalidation, quarantine, recovery, and replica serialization."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fdai.core.executor.lock import ResourceLockManager
from fdai.core.operational_context import (
    OPERATING_INTENT_SOURCE_ADMISSION_KEY,
    StateStoreOperatingIntentAdmissionReader,
)
from fdai.core.risk_gate import OntologyChangeWindowEvidenceProvider
from fdai.delivery.operating_model import JsonOperatingIntentSourceProvider
from fdai.rule_catalog.schema.ontology_catalog import OntologyCatalog, load_ontology_catalog
from fdai.runtime.operating_intent_revalidation import (
    OperatingIntentSourceRevalidationWorker,
)
from fdai.runtime.operating_intent_source import (
    OPERATING_INTENT_SOURCE_LOCK_KEY,
    OPERATING_INTENT_SOURCE_STATUS_KEY,
    OperatingIntentSourceRuntime,
    build_operating_intent_source_runtime,
    project_operating_intent_source_from_env,
)
from fdai.shared.contracts.registry import PackageResourceSchemaRegistry
from fdai.shared.providers.ontology_instance import OntologyLinkRecord, OntologyObjectRecord
from fdai.shared.providers.operating_model import OperatingIntentSourceDocument
from fdai.shared.providers.testing import InMemoryOntologyInstanceStore
from fdai.shared.providers.testing.state_store import InMemoryStateStore

REPO_ROOT = Path(__file__).resolve().parents[4]
_RETRIEVED_AT = datetime(2026, 8, 27, 12, tzinfo=UTC)
_EFFECTIVE_FROM = "2026-08-27T00:00:00+00:00"
_REVISION = "operating-intent-revision-1"
_FRESHNESS_SECONDS = 3600
_INTENT_OBJECT_IDS = (
    "architecture-constraint-1",
    "change-window-1",
    "cost-objective-1",
    "ownership-1",
    "recovery-objective-1",
    "service-objective-1",
)


def _catalog_and_store() -> tuple[OntologyCatalog, InMemoryOntologyInstanceStore]:
    catalog = load_ontology_catalog(
        REPO_ROOT / "rule-catalog",
        schema_registry=PackageResourceSchemaRegistry(),
        probes_root=REPO_ROOT / "rule-catalog" / "probes",
    )
    store = InMemoryOntologyInstanceStore(
        object_types=catalog.object_types,
        link_types=catalog.link_types,
    )
    return catalog, store


def _document() -> dict[str, object]:
    """One complete, currently effective six-type source with declared freshness."""

    return {
        "source_revision": _REVISION,
        "provenance": {
            "source_url": "https://example.invalid/operating-intent-source",
            "resolved_ref": _REVISION,
            "retrieved_at": _RETRIEVED_AT.isoformat(),
        },
        "objects": [
            {
                "id": "service-objective-1",
                "object_type": "ServiceObjective",
                "properties": {
                    "id": "service-objective-1",
                    "objective_kind": "availability",
                    "metric": "availability",
                    "unit": "ratio",
                    "target": 0.999,
                    "window_seconds": 2592000,
                    "measurement_source_ref": "source:service-objectives",
                    "freshness_seconds": _FRESHNESS_SECONDS,
                    "effective_from": _EFFECTIVE_FROM,
                },
            },
            {
                "id": "recovery-objective-1",
                "object_type": "RecoveryObjective",
                "properties": {
                    "id": "recovery-objective-1",
                    "rto_seconds": 3600,
                    "rpo_seconds": 300,
                    "measurement_source_ref": "source:recovery-objectives",
                    "freshness_seconds": _FRESHNESS_SECONDS,
                    "effective_from": _EFFECTIVE_FROM,
                },
            },
            {
                "id": "cost-objective-1",
                "object_type": "CostObjective",
                "properties": {
                    "id": "cost-objective-1",
                    "objective_kind": "monthly_budget",
                    "currency": "USD",
                    "target": 1000,
                    "period_seconds": 2592000,
                    "measurement_source_ref": "source:cost-objectives",
                    "freshness_seconds": _FRESHNESS_SECONDS,
                    "effective_from": _EFFECTIVE_FROM,
                },
            },
            {
                "id": "architecture-constraint-1",
                "object_type": "ArchitectureConstraint",
                "properties": {
                    "id": "architecture-constraint-1",
                    "constraint_kind": "network_isolation",
                    "expression_ref": "policy:network-isolation",
                    "severity": "high",
                    "effective_from": _EFFECTIVE_FROM,
                },
            },
            {
                "id": "ownership-1",
                "object_type": "Ownership",
                "properties": {
                    "id": "ownership-1",
                    "owner_ref": "group:operations-owner",
                    "escalation_ref": "route:on-call",
                    "effective_from": _EFFECTIVE_FROM,
                    "source_ref": "source:service-catalog",
                },
            },
            {
                "id": "change-window-1",
                "object_type": "ChangeWindow",
                "properties": {
                    "id": "change-window-1",
                    "window_kind": "maintenance",
                    "scope_ref": "scope:example",
                    "status": "active",
                    "effective_from": _EFFECTIVE_FROM,
                    "effective_to": "2026-09-30T00:00:00+00:00",
                    "policy_ref": "policy:change-window",
                },
            },
        ],
        "links": [],
    }


def _digest_of(document: Mapping[str, object]) -> str:
    from fdai.delivery.operating_model.json_file import (
        operating_intent_source_document_from_mapping,
    )
    from fdai.shared.providers.operating_model import (
        operating_intent_source_document_digest,
    )

    return operating_intent_source_document_digest(
        operating_intent_source_document_from_mapping(document)
    )


def _env(path: Path, document: Mapping[str, object], **overrides: str) -> dict[str, str]:
    env = {
        "FDAI_OPERATING_INTENT_SOURCE_PATH": str(path),
        "FDAI_OPERATING_INTENT_SOURCE_REVISION": str(document["source_revision"]),
        "FDAI_OPERATING_INTENT_SOURCE_SHA256": _digest_of(document),
    }
    env.update(overrides)
    return env


def _write(path: Path, document: Mapping[str, object]) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def _runtime(
    *,
    path: Path,
    document: Mapping[str, object],
    store: InMemoryOntologyInstanceStore,
    catalog: OntologyCatalog,
    state_store: InMemoryStateStore,
    resource_lock: object | None = None,
    **overrides: str,
) -> OperatingIntentSourceRuntime:
    runtime = build_operating_intent_source_runtime(
        store=store,
        object_types=catalog.object_types,
        link_types=catalog.link_types,
        state_store=state_store,
        environment=_env(path, document, **overrides),
        resource_lock=resource_lock or ResourceLockManager(),  # type: ignore[arg-type]
    )
    assert runtime is not None
    return runtime


async def _admission_status(state_store: InMemoryStateStore, *, now: datetime) -> str:
    admission = await StateStoreOperatingIntentAdmissionReader(state_store).resolve(now=now)
    return admission.status.value


async def _maintenance_authority(
    store: InMemoryOntologyInstanceStore,
    state_store: InMemoryStateStore,
    *,
    at: datetime,
) -> bool:
    provider = OntologyChangeWindowEvidenceProvider(
        store,
        intent_admission=StateStoreOperatingIntentAdmissionReader(state_store),
    )
    return await provider.is_active(target_ref="scope:example", at=at)


async def _all_intent_objects_present(store: InMemoryOntologyInstanceStore) -> bool:
    for identifier in _INTENT_OBJECT_IDS:
        if await store.get_object(identifier) is None:
            return False
    return True


async def test_fresh_at_start_then_stale_quarantines_intent_authority(tmp_path: Path) -> None:
    """Startup admission is a proof about a moment, not a standing grant."""

    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
    )

    fresh_at = _RETRIEVED_AT + timedelta(minutes=1)
    assert await runtime.admit(now=fresh_at) is not None
    assert await _admission_status(state_store, now=fresh_at) == "admitted"
    assert await _maintenance_authority(store, state_store, at=fresh_at) is True

    stale_at = _RETRIEVED_AT + timedelta(seconds=_FRESHNESS_SECONDS + 1)
    await OperatingIntentSourceRevalidationWorker(runtime=runtime).run_once(now=stale_at)

    assert await _admission_status(state_store, now=stale_at) == "quarantined"
    assert await _maintenance_authority(store, state_store, at=stale_at) is False
    # The graph survives as evidence and history; only authority is withdrawn.
    assert await _all_intent_objects_present(store) is True


async def test_missing_source_after_startup_quarantines_without_deleting(
    tmp_path: Path,
) -> None:
    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
    )
    fresh_at = _RETRIEVED_AT + timedelta(minutes=1)
    await runtime.admit(now=fresh_at)

    path.unlink()
    await OperatingIntentSourceRevalidationWorker(runtime=runtime).run_once(now=fresh_at)

    assert await _admission_status(state_store, now=fresh_at) == "quarantined"
    assert await _maintenance_authority(store, state_store, at=fresh_at) is False
    assert await _all_intent_objects_present(store) is True
    status = await state_store.read_state(OPERATING_INTENT_SOURCE_STATUS_KEY)
    assert status is not None
    assert status["status"] == "rejected"


async def test_valid_refresh_readmits_without_a_restart(tmp_path: Path) -> None:
    """Recovery is symmetric with quarantine: the same pass that denied re-admits."""

    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
    )
    fresh_at = _RETRIEVED_AT + timedelta(minutes=1)
    await runtime.admit(now=fresh_at)
    path.unlink()
    worker = OperatingIntentSourceRevalidationWorker(runtime=runtime)
    await worker.run_once(now=fresh_at)
    assert await _maintenance_authority(store, state_store, at=fresh_at) is False

    _write(path, document)
    recovered_at = _RETRIEVED_AT + timedelta(minutes=2)
    await worker.run_once(now=recovered_at)

    assert await _admission_status(state_store, now=recovered_at) == "admitted"
    assert await _maintenance_authority(store, state_store, at=recovered_at) is True
    status = await state_store.read_state(OPERATING_INTENT_SOURCE_STATUS_KEY)
    assert status is not None
    assert status["status"] == "projected"


async def test_cross_release_swap_after_startup_quarantines(tmp_path: Path) -> None:
    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
    )
    fresh_at = _RETRIEVED_AT + timedelta(minutes=1)
    await runtime.admit(now=fresh_at)

    swapped = _document()
    swapped["source_revision"] = "operating-intent-revision-2"
    _write(path, swapped)
    await OperatingIntentSourceRevalidationWorker(runtime=runtime).run_once(now=fresh_at)

    assert await _admission_status(state_store, now=fresh_at) == "quarantined"
    assert await _maintenance_authority(store, state_store, at=fresh_at) is False
    assert await _all_intent_objects_present(store) is True


async def test_admission_expires_when_revalidation_stops(tmp_path: Path) -> None:
    """A worker that stops making progress withdraws authority on its own."""

    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
        FDAI_OPERATING_INTENT_SOURCE_REVALIDATE_SECONDS="60",
    )
    fresh_at = _RETRIEVED_AT + timedelta(minutes=1)
    await runtime.admit(now=fresh_at)

    assert runtime.admission_validity_seconds == 180
    within = fresh_at + timedelta(seconds=180)
    beyond = fresh_at + timedelta(seconds=181)
    assert await _admission_status(state_store, now=within) == "admitted"
    assert await _admission_status(state_store, now=beyond) == "expired"
    assert await _maintenance_authority(store, state_store, at=beyond) is False


class _UnavailableResourceLock:
    """A distributed lock backend that cannot be reached."""

    distributed = True

    @asynccontextmanager
    async def acquire(self, resource_id: str) -> AsyncIterator[None]:
        raise ConnectionError(f"advisory lock backend unreachable for {resource_id}")
        yield  # pragma: no cover - unreachable, keeps the async generator shape


async def test_lock_failure_fails_closed_as_unavailable(tmp_path: Path) -> None:
    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
        resource_lock=_UnavailableResourceLock(),
    )

    fresh_at = _RETRIEVED_AT + timedelta(minutes=1)
    assert await runtime.admit(now=fresh_at) is None

    record = await state_store.read_state(OPERATING_INTENT_SOURCE_ADMISSION_KEY)
    assert record is not None
    assert record["status"] == "unavailable"
    assert await _admission_status(state_store, now=fresh_at) == "unavailable"
    assert await _maintenance_authority(store, state_store, at=fresh_at) is False
    assert await store.get_object("change-window-1") is None


class _CountingOntologyStore(InMemoryOntologyInstanceStore):
    """Count destructive subgraph replacements so a redundant apply is visible."""

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)  # type: ignore[arg-type]
        self.replacements = 0

    async def replace_subgraph(
        self,
        *,
        objects: Sequence[OntologyObjectRecord],
        links: Sequence[OntologyLinkRecord],
        previous_object_ids: Sequence[str] = (),
        previous_link_keys: Sequence[tuple[str, str, str]] = (),
    ) -> None:
        self.replacements += 1
        await super().replace_subgraph(
            objects=objects,
            links=links,
            previous_object_ids=previous_object_ids,
            previous_link_keys=previous_link_keys,
        )


class _SerializationProbe:
    """Wrap one lock and record acquisitions plus peak concurrent holders."""

    distributed = True

    def __init__(self, inner: ResourceLockManager) -> None:
        self._inner = inner
        self.acquired: list[str] = []
        self.held = 0
        self.peak_held = 0

    @asynccontextmanager
    async def acquire(self, resource_id: str) -> AsyncIterator[None]:
        async with self._inner.acquire(resource_id):
            self.acquired.append(resource_id)
            self.held += 1
            self.peak_held = max(self.peak_held, self.held)
            try:
                yield
            finally:
                self.held -= 1


class _ApplyInterleaveStateStore(InMemoryStateStore):
    """Yield control exactly once, while an ``applying`` manifest is in flight.

    That is the only window in which a second replica could misread a peer's
    in-flight apply as an interrupted one, so forcing the interleave here is what
    makes the serialization claim falsifiable rather than scheduler-dependent.
    """

    def __init__(self) -> None:
        super().__init__()
        self._interleaved = False

    async def write_state(self, key: str, value: Mapping[str, object]) -> None:
        await super().write_state(key, value)
        if not self._interleaved and value.get("status") == "applying":
            self._interleaved = True
            await asyncio.sleep(0)


class _RendezvousProvider:
    """Delay every load until both replicas have one, forcing real contention."""

    def __init__(
        self,
        inner: JsonOperatingIntentSourceProvider,
        barrier: asyncio.Barrier,
    ) -> None:
        self._inner = inner
        self._barrier = barrier

    async def load(self) -> OperatingIntentSourceDocument:
        document = await self._inner.load()
        await self._barrier.wait()
        return document


async def test_concurrent_replicas_serialize_manifest_recovery_and_projection(
    tmp_path: Path,
) -> None:
    """Two replicas starting together must not read each other's in-flight apply.

    Without the shared lock the second replica reads the first replica's ``applying``
    manifest, treats it as an interrupted apply, and deletes the subgraph the first
    replica is still writing. The rendezvous makes the overlap deterministic instead
    of relying on scheduler luck.
    """

    catalog, _ = _catalog_and_store()
    store = _CountingOntologyStore(
        object_types=catalog.object_types,
        link_types=catalog.link_types,
    )
    state_store = _ApplyInterleaveStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    shared_lock = _SerializationProbe(ResourceLockManager())
    barrier = asyncio.Barrier(2)
    replicas = [
        _runtime(
            path=path,
            document=document,
            store=store,
            catalog=catalog,
            state_store=state_store,
            resource_lock=shared_lock,
        )
        for _ in range(2)
    ]
    replicas = [
        OperatingIntentSourceRuntime(
            binding=replica.binding,
            provider=_RendezvousProvider(replica.provider, barrier),  # type: ignore[arg-type]
            store=store,
            object_types=replica.object_types,
            link_types=replica.link_types,
            state_store=state_store,
            resource_lock=shared_lock,
        )
        for replica in replicas
    ]

    now = _RETRIEVED_AT + timedelta(minutes=1)
    results = await asyncio.gather(*(replica.admit(now=now) for replica in replicas))

    assert all(result is not None for result in results)
    assert shared_lock.acquired == [OPERATING_INTENT_SOURCE_LOCK_KEY] * 2
    assert shared_lock.peak_held == 1
    # The second replica observed a closed ``projected`` manifest, so it neither
    # re-applied nor ran interrupted-apply recovery over the first replica's graph.
    assert store.replacements == 1
    assert await _all_intent_objects_present(store) is True
    assert await _admission_status(state_store, now=now) == "admitted"
    assert await _maintenance_authority(store, state_store, at=now) is True


async def test_worker_revalidates_on_its_bounded_interval(tmp_path: Path) -> None:
    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
        FDAI_OPERATING_INTENT_SOURCE_REVALIDATE_SECONDS="1",
    )
    await runtime.admit(now=_RETRIEVED_AT + timedelta(minutes=1))
    path.unlink()

    worker = OperatingIntentSourceRevalidationWorker(runtime=runtime)
    assert worker.interval_seconds == 1
    stop = asyncio.Event()
    task = asyncio.create_task(worker.run(stop))
    try:
        while True:
            record = await state_store.read_state(OPERATING_INTENT_SOURCE_ADMISSION_KEY)
            if record is not None and record["status"] == "quarantined":
                break
            await asyncio.sleep(0.05)
    finally:
        stop.set()
        await asyncio.wait_for(task, timeout=5)


async def test_worker_stops_without_revalidating_when_already_stopped(
    tmp_path: Path,
) -> None:
    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
    )
    stop = asyncio.Event()
    stop.set()

    await OperatingIntentSourceRevalidationWorker(runtime=runtime).run(stop)

    assert await state_store.read_state(OPERATING_INTENT_SOURCE_ADMISSION_KEY) is None


def test_revalidation_interval_beyond_the_admission_bound_is_rejected(
    tmp_path: Path,
) -> None:
    catalog, store = _catalog_and_store()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)

    with pytest.raises(ValueError, match="admission validity bound"):
        _runtime(
            path=path,
            document=document,
            store=store,
            catalog=catalog,
            state_store=InMemoryStateStore(),
            FDAI_OPERATING_INTENT_SOURCE_REVALIDATE_SECONDS="30000",
        )


async def test_unconfigured_release_holds_the_same_lock(tmp_path: Path) -> None:
    """Releasing an owned subgraph is a destructive projection, so it serializes too."""

    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    shared_lock = _SerializationProbe(ResourceLockManager())
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
        resource_lock=shared_lock,
    )
    await runtime.admit(now=_RETRIEVED_AT + timedelta(minutes=1))

    await project_operating_intent_source_from_env(
        store=store,
        object_types=catalog.object_types,
        link_types=catalog.link_types,
        status_store=state_store,
        env={},
        resource_lock=shared_lock,
    )

    assert shared_lock.acquired == [OPERATING_INTENT_SOURCE_LOCK_KEY] * 2
    assert await store.get_object("change-window-1") is None


async def test_unconfigured_release_fails_closed_when_the_lock_is_unavailable(
    tmp_path: Path,
) -> None:
    catalog, store = _catalog_and_store()
    state_store = InMemoryStateStore()
    path = tmp_path / "operating-intent-source.json"
    document = _document()
    _write(path, document)
    runtime = _runtime(
        path=path,
        document=document,
        store=store,
        catalog=catalog,
        state_store=state_store,
    )
    now = _RETRIEVED_AT + timedelta(minutes=1)
    await runtime.admit(now=now)

    await project_operating_intent_source_from_env(
        store=store,
        object_types=catalog.object_types,
        link_types=catalog.link_types,
        status_store=state_store,
        env={},
        resource_lock=_UnavailableResourceLock(),
    )

    # Nothing was cleared, but the denying admission means nothing is granted either.
    assert await store.get_object("change-window-1") is not None
    assert await _admission_status(state_store, now=now) == "unavailable"
    assert await _maintenance_authority(store, state_store, at=now) is False
