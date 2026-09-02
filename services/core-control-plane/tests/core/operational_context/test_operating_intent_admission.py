"""Current-admission gating for deployment-owned operating-intent authority."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fdai.core.operational_context import (
    OPERATING_INTENT_SOURCE_ADMISSION_KEY,
    OperatingIntentAdmissionStatus,
    StateStoreOperatingIntentAdmissionReader,
    evaluate_operating_intent_admission,
)
from fdai.shared.providers.testing.state_store import InMemoryStateStore

_NOW = datetime(2026, 8, 27, 12, tzinfo=UTC)
_DIGEST = f"sha256:{'a' * 64}"


def _admitted(**overrides: object) -> dict[str, object]:
    record: dict[str, object] = {
        "schema_version": "1.0.0",
        "status": "admitted",
        "source_revision": "operating-intent-revision-1",
        "snapshot_digest": _DIGEST,
        "validated_at": (_NOW - timedelta(minutes=1)).isoformat(),
        "max_age_seconds": 900,
    }
    record.update(overrides)
    return record


def test_absent_record_neither_grants_nor_withholds() -> None:
    admission = evaluate_operating_intent_admission(None, now=_NOW)

    assert admission.status is OperatingIntentAdmissionStatus.UNBOUND
    assert admission.grants_intent_authority is True


def test_unconfigured_binding_does_not_withhold_generic_behavior() -> None:
    admission = evaluate_operating_intent_admission(
        {"schema_version": "1.0.0", "status": "unconfigured"},
        now=_NOW,
    )

    assert admission.status is OperatingIntentAdmissionStatus.UNCONFIGURED
    assert admission.grants_intent_authority is True


def test_current_admission_grants_and_carries_pinned_identity() -> None:
    admission = evaluate_operating_intent_admission(_admitted(), now=_NOW)

    assert admission.status is OperatingIntentAdmissionStatus.ADMITTED
    assert admission.grants_intent_authority is True
    assert admission.source_revision == "operating-intent-revision-1"
    assert admission.snapshot_digest == _DIGEST


def test_admission_expires_without_revalidation() -> None:
    """An old proof is not a current one, even though its status still reads admitted."""

    admission = evaluate_operating_intent_admission(
        _admitted(),
        now=_NOW + timedelta(seconds=901),
    )

    assert admission.status is OperatingIntentAdmissionStatus.EXPIRED
    assert admission.grants_intent_authority is False


def test_quarantined_and_unavailable_deny() -> None:
    for status, expected in (
        ("quarantined", OperatingIntentAdmissionStatus.QUARANTINED),
        ("unavailable", OperatingIntentAdmissionStatus.UNAVAILABLE),
    ):
        admission = evaluate_operating_intent_admission(
            {
                "schema_version": "1.0.0",
                "status": status,
                "reason": "source is not currently effective (stale)",
                "validated_at": _NOW.isoformat(),
            },
            now=_NOW,
        )

        assert admission.status is expected
        assert admission.grants_intent_authority is False
        assert admission.reason == "source is not currently effective (stale)"


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "projected"},
        {"source_revision": ""},
        {"snapshot_digest": "not-a-digest"},
        {"validated_at": "not-a-timestamp"},
        {"validated_at": "2026-08-27T12:00:00"},
        {"max_age_seconds": 0},
        {"max_age_seconds": 86_401},
        {"max_age_seconds": True},
    ],
)
def test_malformed_admission_denies(overrides: dict[str, object]) -> None:
    admission = evaluate_operating_intent_admission(_admitted(**overrides), now=_NOW)

    assert admission.status is OperatingIntentAdmissionStatus.MALFORMED
    assert admission.grants_intent_authority is False


def test_naive_now_is_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        evaluate_operating_intent_admission(_admitted(), now=datetime(2026, 8, 27, 12))


async def test_state_store_reader_resolves_the_durable_record() -> None:
    store = InMemoryStateStore()
    await store.write_state(OPERATING_INTENT_SOURCE_ADMISSION_KEY, _admitted())

    admission = await StateStoreOperatingIntentAdmissionReader(store).resolve(now=_NOW)

    assert admission.status is OperatingIntentAdmissionStatus.ADMITTED
