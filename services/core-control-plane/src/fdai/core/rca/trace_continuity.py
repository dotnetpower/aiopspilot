"""Evidence-bounded deterministic RCA for distributed trace discontinuities."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fdai.core.detection.trace_continuity import (
    TraceContinuityReason,
    TraceContinuityResult,
    TraceContinuityState,
)
from fdai.core.rca.contract import (
    CauseDomain,
    Citation,
    CitationKind,
    RcaOutcome,
    RcaResult,
    RcaTier,
    RootCauseHypothesis,
)
from fdai.core.rca.grounding import enforce_grounding

_MAX_AFFECTED_ITEMS = 32
_MAX_AFFECTED_TEXT_CHARS = 1024
_MAX_EVIDENCE_REFS = 100


class TraceRcaCause(StrEnum):
    """Reviewed trace-discontinuity cause classes."""

    INSTRUMENTATION = "instrumentation"
    COLLECTOR = "collector"
    HEADER_PROPAGATION = "header_propagation"


@dataclass(frozen=True, slots=True)
class TraceCauseEvidence:
    """Independent telemetry evidence supporting one bounded cause class."""

    cause: TraceRcaCause
    topology_ref: str
    scenario_id: str
    window_bucket: str
    observed_at: datetime
    affected_items: tuple[str, ...]
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("topology_ref", self.topology_ref),
            ("scenario_id", self.scenario_id),
            ("window_bucket", self.window_bucket),
        ):
            if not value or value != value.strip() or len(value) > 512:
                raise ValueError(f"trace cause {name} MUST be bounded non-empty text")
        if self.observed_at.tzinfo is None:
            raise ValueError("trace cause observed_at MUST be timezone-aware")
        if not 1 <= len(self.affected_items) <= _MAX_AFFECTED_ITEMS:
            raise ValueError(
                f"trace cause affected_items MUST contain 1 to {_MAX_AFFECTED_ITEMS} items"
            )
        if not 1 <= len(self.evidence_refs) <= _MAX_EVIDENCE_REFS:
            raise ValueError(
                f"trace cause evidence_refs MUST contain 1 to {_MAX_EVIDENCE_REFS} items"
            )
        if any(not item or item != item.strip() or len(item) > 128 for item in self.affected_items):
            raise ValueError("trace cause affected_items MUST be bounded non-empty text")
        if sum(map(len, self.affected_items)) > _MAX_AFFECTED_TEXT_CHARS:
            raise ValueError(
                f"trace cause affected_items MUST contain at most "
                f"{_MAX_AFFECTED_TEXT_CHARS} characters"
            )
        if any(not ref or ref != ref.strip() or len(ref) > 512 for ref in self.evidence_refs):
            raise ValueError("trace cause evidence_refs MUST be bounded non-empty text")
        if len(set(self.affected_items)) != len(self.affected_items):
            raise ValueError("trace cause affected_items MUST be unique")
        if len(set(self.evidence_refs)) != len(self.evidence_refs):
            raise ValueError("trace cause evidence_refs MUST be unique")
        object.__setattr__(self, "affected_items", tuple(sorted(self.affected_items)))
        object.__setattr__(self, "evidence_refs", tuple(sorted(self.evidence_refs)))


def analyze_trace_continuity_cause(
    result: TraceContinuityResult,
    *,
    cause_evidence: tuple[TraceCauseEvidence, ...],
    min_confidence: float = 0.0,
) -> RcaResult:
    """Return one cited T1 cause or hold when evidence is absent or conflicting."""

    if result.state is not TraceContinuityState.DISCONTINUOUS:
        return _abstained("trace_not_discontinuous")
    if not result.evidence_refs:
        return _abstained("trace_continuity_evidence_missing")
    if not cause_evidence:
        return _abstained("trace_cause_evidence_missing")
    if len(cause_evidence) != 1:
        return _abstained("trace_cause_evidence_conflicting")

    selected = cause_evidence[0]
    if not _evidence_matches(result, selected):
        return _abstained("trace_cause_evidence_scope_mismatch")

    citations = tuple(
        Citation(kind=CitationKind.TELEMETRY, ref=ref)
        for ref in dict.fromkeys((*result.evidence_refs, *selected.evidence_refs))
    )
    hypothesis = RootCauseHypothesis(
        tier=RcaTier.T1,
        cause=_cause_text(selected),
        confidence=0.9,
        citations=citations,
        cause_domain=_cause_domain(selected.cause),
        evidence_refs=tuple(citation.ref for citation in citations),
        remediation_ref=None,
    )
    return enforce_grounding(hypothesis, min_confidence=min_confidence)


def _evidence_matches(
    result: TraceContinuityResult,
    evidence: TraceCauseEvidence,
) -> bool:
    if (
        evidence.topology_ref != result.topology_ref
        or evidence.scenario_id != result.scenario_id
        or evidence.window_bucket != result.window_bucket
        or result.observed_at is None
        or evidence.observed_at > result.observed_at
    ):
        return False
    affected = set(evidence.affected_items)
    if evidence.cause is TraceRcaCause.HEADER_PROPAGATION:
        allowed = set(result.disconnected_boundaries)
        if result.reason is TraceContinuityReason.CONTEXT_DROPPED:
            allowed.update(_missing_hop_boundaries(result))
        return (
            result.reason
            in {
                TraceContinuityReason.CONTEXT_REGENERATED,
                TraceContinuityReason.CONTEXT_DROPPED,
            }
            and affected <= allowed
        )
    if evidence.cause is TraceRcaCause.INSTRUMENTATION:
        allowed_hops = (
            set(result.missing_hops)
            if result.reason is TraceContinuityReason.CONTEXT_DROPPED
            else set(result.observed_hops)
        )
        return (
            result.reason
            in {
                TraceContinuityReason.CONTEXT_DROPPED,
                TraceContinuityReason.HOP_ORDER_INVALID,
            }
            and affected <= allowed_hops
        )
    return result.reason is TraceContinuityReason.CONTEXT_DROPPED and affected <= set(
        result.missing_hops
    )


def _missing_hop_boundaries(result: TraceContinuityResult) -> tuple[str, ...]:
    missing = set(result.missing_hops)
    return tuple(
        f"{upstream}->{downstream}"
        for upstream, downstream in zip(
            result.expected_hops,
            result.expected_hops[1:],
            strict=False,
        )
        if upstream in missing or downstream in missing
    )


def _cause_text(evidence: TraceCauseEvidence) -> str:
    targets = ", ".join(evidence.affected_items)
    if evidence.cause is TraceRcaCause.INSTRUMENTATION:
        return f"trace instrumentation missing or invalid at hops: {targets}"
    if evidence.cause is TraceRcaCause.COLLECTOR:
        return f"telemetry collector did not retain spans for hops: {targets}"
    return f"trace context propagation failed at boundaries: {targets}"


def _cause_domain(cause: TraceRcaCause) -> CauseDomain:
    if cause is TraceRcaCause.COLLECTOR:
        return CauseDomain.SHARED_DEPENDENCY
    return CauseDomain.APPLICATION


def _abstained(reason: str) -> RcaResult:
    return RcaResult(
        outcome=RcaOutcome.ABSTAINED,
        hypothesis=None,
        reason=reason,
    )


__all__ = [
    "TraceCauseEvidence",
    "TraceRcaCause",
    "analyze_trace_continuity_cause",
]
