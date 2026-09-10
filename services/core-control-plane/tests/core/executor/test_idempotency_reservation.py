"""Crash-safe idempotency reservation contract tests."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fdai.core.executor import idempotency_reservation as reservation_model
from fdai.core.executor.idempotency_reservation import (
    IdempotencyReservationIdentity,
    IdempotencyReservationRecord,
    IdempotencyReservationReserveResult,
    IdempotencyReservationTransitionReceipt,
    ReservationEvidenceKind,
    ReservationMatch,
    ReservationState,
    begin_dispatch,
    classify_reservation,
    complete_reservation,
    dispatch_permitted,
    expire_reservation,
    reopen_reservation,
    reservation_record_from_mapping,
    reservation_record_to_mapping,
)
from fdai.shared.contracts.models import ExecutionPath
from fdai.shared.providers.resource_lock import (
    ResourceLockAcquisitionReceipt,
    ResourceLockAcquisitionRequest,
)

_NOW = datetime(2026, 9, 10, 8, 0, tzinfo=UTC)
_SOURCE_REVISION = "commit:" + "a" * 40
_DIGEST = "sha256:" + "b" * 64


def _identity(
    *,
    idempotency_key: str = "example-idempotency",
    action_digest: str = "sha256:" + "1" * 64,
    path: ExecutionPath = ExecutionPath.DIRECT_API,
    owner_reference_digest: str = "sha256:" + "2" * 64,
    attempt: int = 1,
    target_ref: str = "resource/example",
    acquired_at: datetime = _NOW,
) -> IdempotencyReservationIdentity:
    request = ResourceLockAcquisitionRequest.create(
        target_ref=target_ref,
        action_digest=action_digest,
        attempt=attempt,
        producer_id="fdai.core.executor",
        producer_version="1.0.0",
        source_revision=_SOURCE_REVISION,
    )
    receipt = ResourceLockAcquisitionReceipt.create(
        lock_key=request.lock_key,
        target_digest=request.target_digest,
        action_digest=request.action_digest,
        attempt=request.attempt,
        provider_id="local-resource-lock",
        provider_version="1.0.0",
        producer_id=request.producer_id,
        producer_version=request.producer_version,
        owner_token_digest=owner_reference_digest,
        fencing_generation=None,
        session_identity="session:example",
        provider_attestation_digest="sha256:" + "3" * 64,
        trust_anchor_id="fdai:local-test-only",
        acquired_at=acquired_at,
        valid_until=None,
        source_revision=request.source_revision,
        request_digest=request.request_digest,
    )
    return IdempotencyReservationIdentity.create(
        idempotency_key=idempotency_key,
        action_digest=action_digest,
        execution_path=path,
        execution_fingerprint="4" * 64,
        source_revision=_SOURCE_REVISION,
        acquisition_receipt=receipt,
    )


def _reserved() -> IdempotencyReservationRecord:
    return IdempotencyReservationRecord.create_reserved(
        identity=_identity(),
        reserved_at=_NOW,
        lease_expires_at=_NOW + timedelta(seconds=10),
    )


def test_reserve_dispatch_and_terminal_transition_are_monotonic() -> None:
    reserved = _reserved()
    in_flight = begin_dispatch(reserved, at=_NOW + timedelta(seconds=1))
    terminal = complete_reservation(
        in_flight,
        at=_NOW + timedelta(seconds=2),
        terminal_outcome_digest="sha256:" + "5" * 64,
        authoritative_status_digest="sha256:" + "6" * 64,
    )

    assert reserved.state is ReservationState.RESERVED
    assert in_flight.state is ReservationState.IN_FLIGHT
    assert terminal.state is ReservationState.TERMINAL
    assert [reserved.revision, in_flight.revision, terminal.revision] == [1, 2, 3]
    assert terminal.execution_authority is False
    assert terminal.effect_verified is False


def test_expired_in_flight_becomes_unknown_and_cannot_redispatch() -> None:
    in_flight = begin_dispatch(_reserved(), at=_NOW + timedelta(seconds=1))
    unknown = expire_reservation(in_flight, at=_NOW + timedelta(seconds=10))

    assert unknown.state is ReservationState.OUTCOME_UNKNOWN
    assert unknown.evidence_kind is ReservationEvidenceKind.LEASE_EXPIRED
    assert dispatch_permitted(unknown, at=_NOW + timedelta(seconds=11)) is False
    with pytest.raises(ValueError, match="not eligible"):
        begin_dispatch(unknown, at=_NOW + timedelta(seconds=11))


def test_abandoned_requires_authoritative_proof_dispatch_never_began() -> None:
    reserved = _reserved()
    with pytest.raises(ValueError, match="requires proof"):
        expire_reservation(reserved, at=reserved.lease_expires_at)

    abandoned = expire_reservation(
        reserved,
        at=reserved.lease_expires_at,
        dispatch_never_began_digest=_DIGEST,
    )
    assert abandoned.state is ReservationState.ABANDONED
    assert abandoned.dispatch_started_at is None
    assert dispatch_permitted(abandoned, at=reserved.lease_expires_at) is False


def test_unknown_requires_authoritative_terminal_resolution() -> None:
    unknown = expire_reservation(
        begin_dispatch(_reserved(), at=_NOW + timedelta(seconds=1)),
        at=_NOW + timedelta(seconds=10),
    )
    resolved = complete_reservation(
        unknown,
        at=_NOW + timedelta(seconds=11),
        terminal_outcome_digest="sha256:" + "7" * 64,
        authoritative_status_digest="sha256:" + "8" * 64,
        irrevocable_non_acceptance=True,
    )

    assert resolved.state is ReservationState.TERMINAL
    assert resolved.evidence_kind is ReservationEvidenceKind.IRREVOCABLE_NON_ACCEPTANCE


def test_duplicate_same_and_conflict_are_distinct() -> None:
    existing = _reserved()
    same = _identity()
    conflict = _identity(action_digest="sha256:" + "9" * 64)
    other_key = _identity(idempotency_key="other")

    assert classify_reservation(None, same) is ReservationMatch.ACQUIRED
    assert classify_reservation(existing, same) is ReservationMatch.DUPLICATE_SAME
    assert classify_reservation(existing, conflict) is ReservationMatch.CONFLICT
    assert classify_reservation(existing, other_key) is ReservationMatch.ACQUIRED


def test_transition_receipt_binds_cas_revision_and_readback() -> None:
    record = _reserved()
    receipt = IdempotencyReservationTransitionReceipt.create(
        prior_record=None,
        record=record,
        expected_prior_revision=0,
        store_receipt_digest="sha256:" + "a" * 64,
        recorded_at=_NOW,
    )

    assert receipt.execution_authority is False
    assert receipt.effect_verified is False
    with pytest.raises(ValueError, match="revision mismatched"):
        replace(receipt, expected_prior_revision=1)
    with pytest.raises(ValueError, match="digest mismatched"):
        replace(receipt, receipt_digest="sha256:" + "0" * 64)
    result = IdempotencyReservationReserveResult(
        candidate_identity=record.identity,
        match=ReservationMatch.ACQUIRED,
        observed_record=record,
        transition_receipt=receipt,
    )
    assert result.observed_record is record
    with pytest.raises(ValueError, match="mismatched its candidate"):
        IdempotencyReservationReserveResult(
            candidate_identity=_identity(path=ExecutionPath.TOOL_CALL),
            match=ReservationMatch.DUPLICATE_SAME,
            observed_record=record,
            transition_receipt=None,
        )


def test_identity_rejects_acquisition_and_action_substitution() -> None:
    identity = _identity()
    with pytest.raises(ValueError, match="acquisition context mismatched"):
        replace(identity, action_digest="sha256:" + "9" * 64)
    with pytest.raises(ValueError, match="identity digest mismatched"):
        replace(identity, idempotency_key="other")


def test_acquisition_substitution_is_a_conflict() -> None:
    existing = _reserved()
    replacement = _identity(
        owner_reference_digest="sha256:" + "9" * 64,
    )
    assert classify_reservation(existing, replacement) is ReservationMatch.CONFLICT


def test_invalid_state_shape_and_time_fail_closed() -> None:
    reserved = _reserved()
    with pytest.raises(ValueError, match="later-phase evidence"):
        replace(
            reserved,
            evidence_kind=ReservationEvidenceKind.LEASE_EXPIRED,
            evidence_digest=_DIGEST,
        )
    with pytest.raises(ValueError, match="lease has not expired"):
        expire_reservation(reserved, at=_NOW + timedelta(seconds=9))
    with pytest.raises(ValueError, match="predates current state"):
        complete_reservation(
            begin_dispatch(reserved, at=_NOW + timedelta(seconds=1)),
            at=_NOW,
            terminal_outcome_digest=_DIGEST,
            authoritative_status_digest=_DIGEST,
        )


def test_transition_receipt_requires_exact_predecessor_and_legal_edge() -> None:
    reserved = _reserved()
    in_flight = begin_dispatch(reserved, at=_NOW + timedelta(seconds=1))
    receipt = IdempotencyReservationTransitionReceipt.create(
        prior_record=reserved,
        record=in_flight,
        expected_prior_revision=1,
        store_receipt_digest=_DIGEST,
        recorded_at=_NOW + timedelta(seconds=1),
    )
    assert receipt.prior_record is reserved
    with pytest.raises(ValueError, match="requires its predecessor"):
        replace(receipt, prior_record=None)
    abandoned = expire_reservation(
        reserved,
        at=reserved.lease_expires_at,
        dispatch_never_began_digest=_DIGEST,
    )
    terminal = complete_reservation(
        in_flight,
        at=_NOW + timedelta(seconds=2),
        terminal_outcome_digest="sha256:" + "7" * 64,
        authoritative_status_digest="sha256:" + "8" * 64,
    )
    with pytest.raises(ValueError, match="transition edge is invalid"):
        IdempotencyReservationTransitionReceipt.create(
            prior_record=abandoned,
            expected_prior_revision=2,
            record=terminal,
            store_receipt_digest=_DIGEST,
            recorded_at=_NOW + timedelta(seconds=10),
        )


def test_transition_receipt_rejects_lease_rewrite() -> None:
    reserved = _reserved()
    rewritten_reserved = IdempotencyReservationRecord.create_reserved(
        identity=reserved.identity,
        reserved_at=_NOW + timedelta(seconds=1),
        lease_expires_at=_NOW + timedelta(seconds=20),
    )
    rewritten = begin_dispatch(
        rewritten_reserved,
        at=_NOW + timedelta(seconds=2),
    )
    with pytest.raises(ValueError):
        IdempotencyReservationTransitionReceipt.create(
            prior_record=reserved,
            record=rewritten,
            expected_prior_revision=1,
            store_receipt_digest=_DIGEST,
            recorded_at=_NOW + timedelta(seconds=1),
        )


def test_transition_receipt_rejects_dispatch_time_substitution() -> None:
    reserved = _reserved()
    prior = begin_dispatch(reserved, at=_NOW + timedelta(seconds=1))
    substituted_dispatch = begin_dispatch(
        reserved,
        at=_NOW + timedelta(seconds=2),
    )
    terminal = complete_reservation(
        substituted_dispatch,
        at=_NOW + timedelta(seconds=3),
        terminal_outcome_digest="sha256:" + "7" * 64,
        authoritative_status_digest="sha256:" + "8" * 64,
    )
    with pytest.raises(ValueError, match="rewrote dispatch time"):
        IdempotencyReservationTransitionReceipt.create(
            prior_record=prior,
            record=terminal,
            expected_prior_revision=prior.revision,
            store_receipt_digest=_DIGEST,
            recorded_at=_NOW + timedelta(seconds=3),
        )


def test_authoritative_non_dispatch_allows_higher_attempt_recovery() -> None:
    reserved = _reserved()
    abandoned = expire_reservation(
        reserved,
        at=reserved.lease_expires_at,
        dispatch_never_began_digest=_DIGEST,
    )
    recovered = reopen_reservation(
        abandoned,
        candidate_identity=_identity(
            attempt=2,
            acquired_at=_NOW + timedelta(seconds=10),
        ),
        reserved_at=_NOW + timedelta(seconds=11),
        lease_expires_at=_NOW + timedelta(seconds=20),
    )
    transition = IdempotencyReservationTransitionReceipt.create(
        prior_record=abandoned,
        record=recovered,
        expected_prior_revision=abandoned.revision,
        store_receipt_digest=_DIGEST,
        recorded_at=_NOW + timedelta(seconds=11),
    )

    assert recovered.state is ReservationState.RESERVED
    assert recovered.identity.acquisition_receipt.attempt == 2
    assert transition.record is recovered
    with pytest.raises(ValueError, match="changes the stable operation"):
        reopen_reservation(
            abandoned,
            candidate_identity=_identity(
                attempt=2,
                target_ref="resource/other",
                acquired_at=_NOW + timedelta(seconds=10),
            ),
            reserved_at=_NOW + timedelta(seconds=11),
            lease_expires_at=_NOW + timedelta(seconds=20),
        )


def test_terminal_and_recovery_cannot_predate_predecessor_state() -> None:
    in_flight = begin_dispatch(_reserved(), at=_NOW + timedelta(seconds=1))
    unknown = expire_reservation(
        in_flight,
        at=in_flight.lease_expires_at,
    )
    with pytest.raises(ValueError, match="predates current state"):
        complete_reservation(
            unknown,
            at=_NOW + timedelta(seconds=2),
            terminal_outcome_digest="sha256:" + "7" * 64,
            authoritative_status_digest="sha256:" + "8" * 64,
        )

    abandoned = expire_reservation(
        _reserved(),
        at=_NOW + timedelta(seconds=10),
        dispatch_never_began_digest=_DIGEST,
    )
    with pytest.raises(ValueError, match="predates its predecessor"):
        reopen_reservation(
            abandoned,
            candidate_identity=_identity(
                attempt=2,
                acquired_at=_NOW + timedelta(seconds=10),
            ),
            reserved_at=_NOW + timedelta(seconds=2),
            lease_expires_at=_NOW + timedelta(seconds=20),
        )


def test_reservation_cannot_predate_lock_acquisition() -> None:
    identity = _identity(acquired_at=_NOW + timedelta(seconds=1))
    with pytest.raises(ValueError, match="predates its lock acquisition"):
        IdempotencyReservationRecord.create_reserved(
            identity=identity,
            reserved_at=_NOW,
            lease_expires_at=_NOW + timedelta(seconds=10),
        )


def test_transition_receipt_rejects_backdated_recovery_acquisition() -> None:
    predecessor = expire_reservation(
        _reserved(),
        at=_NOW + timedelta(seconds=10),
        dispatch_never_began_digest=_DIGEST,
    )
    reconstructed = reservation_model._build_record(  # noqa: SLF001
        identity=_identity(
            attempt=2,
            acquired_at=_NOW + timedelta(seconds=5),
        ),
        state=ReservationState.RESERVED,
        revision=predecessor.revision + 1,
        reserved_at=_NOW + timedelta(seconds=11),
        lease_expires_at=_NOW + timedelta(seconds=20),
        state_changed_at=_NOW + timedelta(seconds=11),
    )
    with pytest.raises(ValueError, match="recovery acquisition time is invalid"):
        IdempotencyReservationTransitionReceipt.create(
            prior_record=predecessor,
            record=reconstructed,
            expected_prior_revision=predecessor.revision,
            store_receipt_digest=_DIGEST,
            recorded_at=_NOW + timedelta(seconds=11),
        )


def test_reservation_record_mapping_round_trip_is_exact() -> None:
    record = expire_reservation(
        begin_dispatch(_reserved(), at=_NOW + timedelta(seconds=1)),
        at=_NOW + timedelta(seconds=10),
    )
    mapping = reservation_record_to_mapping(record)

    assert reservation_record_from_mapping(mapping) == record
    with pytest.raises(ValueError, match="fields are invalid"):
        reservation_record_from_mapping({**mapping, "unexpected": True})


def test_reservation_record_mapping_rejects_corruption() -> None:
    mapping = reservation_record_to_mapping(_reserved())
    identity = cast(dict[str, object], mapping["identity"])
    acquisition = cast(dict[str, object], identity["acquisition_receipt"])

    with pytest.raises(ValueError, match="digest mismatched"):
        reservation_record_from_mapping(
            {
                **mapping,
                "record_digest": "sha256:" + "0" * 64,
            }
        )
    with pytest.raises(ValueError, match="MUST be an ISO 8601 timestamp"):
        reservation_record_from_mapping(
            {
                **mapping,
                "reserved_at": "not-a-time",
            }
        )
    with pytest.raises(ValueError):
        reservation_record_from_mapping(
            {
                **mapping,
                "identity": {
                    **identity,
                    "acquisition_receipt": {
                        **acquisition,
                        "execution_authority": True,
                    },
                },
            }
        )
