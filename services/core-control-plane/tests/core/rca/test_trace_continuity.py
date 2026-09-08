"""Evidence-bounded RCA for distributed trace continuity findings."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fdai.core.detection.trace_continuity import (
    TraceContinuityDetector,
    TraceSpanObservation,
    TraceTopologyObservation,
)
from fdai.core.rca import (
    CauseDomain,
    CitationKind,
    RcaOutcome,
    RcaTier,
    TraceCauseEvidence,
    TraceRcaCause,
    analyze_trace_continuity_cause,
)

_NOW = datetime(2026, 9, 9, 0, 0, tzinfo=UTC)
_HOPS = ("app-gateway", "application", "agent", "api-gateway", "model-endpoint")


def _span(trace_id: str, hop: str, sequence: int) -> TraceSpanObservation:
    return TraceSpanObservation(
        trace_id=trace_id,
        span_id=f"span-{sequence}",
        hop=hop,
        sequence=sequence,
        observed_at=_NOW + timedelta(seconds=sequence),
        evidence_ref=f"telemetry:span-{sequence}",
    )


def _result(*, missing_hop: str | None = None, regenerate_at: int | None = None):
    spans = tuple(
        _span(
            "trace-front" if regenerate_at is None or sequence < regenerate_at else "trace-back",
            hop,
            sequence,
        )
        for sequence, hop in enumerate(_HOPS)
        if hop != missing_hop
    )
    return TraceContinuityDetector(clock=lambda: _NOW).evaluate(
        TraceTopologyObservation(
            topology_ref="synthetic-agent-request",
            scenario_id="scenario-trace-1",
            resource_ref="trace-topology/synthetic-agent-request",
            window_bucket="2026-09-09T00:00Z",
            expected_hops=_HOPS,
            spans=spans,
            completed=True,
        )
    )


def _evidence(
    cause: TraceRcaCause,
    *affected_items: str,
) -> TraceCauseEvidence:
    return TraceCauseEvidence(
        cause=cause,
        affected_items=affected_items,
        evidence_refs=(f"telemetry:cause:{cause.value}",),
    )


def test_header_propagation_cause_requires_the_observed_boundary() -> None:
    result = analyze_trace_continuity_cause(
        _result(regenerate_at=2),
        cause_evidence=(
            _evidence(
                TraceRcaCause.HEADER_PROPAGATION,
                "application->agent",
            ),
        ),
    )

    assert result.outcome is RcaOutcome.GROUNDED
    assert result.hypothesis is not None
    assert result.hypothesis.tier is RcaTier.T1
    assert result.hypothesis.cause_domain is CauseDomain.APPLICATION
    assert "application->agent" in result.hypothesis.cause
    assert result.hypothesis.remediation_ref is None
    assert all(citation.kind is CitationKind.TELEMETRY for citation in result.hypothesis.citations)


@pytest.mark.parametrize(
    ("cause", "domain", "cause_text"),
    [
        (TraceRcaCause.INSTRUMENTATION, CauseDomain.APPLICATION, "instrumentation"),
        (TraceRcaCause.COLLECTOR, CauseDomain.SHARED_DEPENDENCY, "collector"),
    ],
)
def test_missing_hop_distinguishes_independently_cited_causes(
    cause: TraceRcaCause,
    domain: CauseDomain,
    cause_text: str,
) -> None:
    result = analyze_trace_continuity_cause(
        _result(missing_hop="agent"),
        cause_evidence=(_evidence(cause, "agent"),),
    )

    assert result.outcome is RcaOutcome.GROUNDED
    assert result.hypothesis is not None
    assert result.hypothesis.cause_domain is domain
    assert cause_text in result.hypothesis.cause
    assert result.hypothesis.remediation_ref is None


def test_dropped_context_can_cite_an_adjacent_header_boundary() -> None:
    result = analyze_trace_continuity_cause(
        _result(missing_hop="agent"),
        cause_evidence=(
            _evidence(
                TraceRcaCause.HEADER_PROPAGATION,
                "application->agent",
            ),
        ),
    )

    assert result.outcome is RcaOutcome.GROUNDED
    assert result.hypothesis is not None
    assert "header" not in result.hypothesis.cause
    assert "context propagation" in result.hypothesis.cause


def test_missing_cause_evidence_holds_for_review() -> None:
    result = analyze_trace_continuity_cause(
        _result(missing_hop="agent"),
        cause_evidence=(),
    )

    assert result.outcome is RcaOutcome.ABSTAINED
    assert result.reason == "trace_cause_evidence_missing"


def test_conflicting_cause_evidence_holds_for_review() -> None:
    result = analyze_trace_continuity_cause(
        _result(missing_hop="agent"),
        cause_evidence=(
            _evidence(TraceRcaCause.INSTRUMENTATION, "agent"),
            _evidence(TraceRcaCause.COLLECTOR, "agent"),
        ),
    )

    assert result.outcome is RcaOutcome.ABSTAINED
    assert result.reason == "trace_cause_evidence_conflicting"


def test_mismatched_cause_scope_holds_for_review() -> None:
    result = analyze_trace_continuity_cause(
        _result(regenerate_at=2),
        cause_evidence=(
            _evidence(
                TraceRcaCause.HEADER_PROPAGATION,
                "agent->api-gateway",
            ),
        ),
    )

    assert result.outcome is RcaOutcome.ABSTAINED
    assert result.reason == "trace_cause_evidence_scope_mismatch"


def test_continuous_trace_never_produces_a_cause() -> None:
    result = analyze_trace_continuity_cause(
        _result(),
        cause_evidence=(_evidence(TraceRcaCause.INSTRUMENTATION, "agent"),),
    )

    assert result.outcome is RcaOutcome.ABSTAINED
    assert result.reason == "trace_not_discontinuous"


def test_trace_cause_evidence_is_bounded_and_unique() -> None:
    with pytest.raises(ValueError, match="affected_items MUST be unique"):
        _evidence(TraceRcaCause.INSTRUMENTATION, "agent", "agent")

    with pytest.raises(ValueError, match="evidence_refs MUST contain 1"):
        TraceCauseEvidence(
            cause=TraceRcaCause.COLLECTOR,
            affected_items=("agent",),
            evidence_refs=(),
        )


def test_trace_cause_evidence_rejects_whitespace_and_canonicalizes_order() -> None:
    with pytest.raises(ValueError, match="bounded non-empty text"):
        _evidence(TraceRcaCause.INSTRUMENTATION, " agent")

    evidence = TraceCauseEvidence(
        cause=TraceRcaCause.HEADER_PROPAGATION,
        affected_items=("agent->api-gateway", "application->agent"),
        evidence_refs=("telemetry:z", "telemetry:a"),
    )

    assert evidence.affected_items == ("agent->api-gateway", "application->agent")
    assert evidence.evidence_refs == ("telemetry:a", "telemetry:z")
