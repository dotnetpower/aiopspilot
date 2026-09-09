"""Azure observation adapters for WAF and CAF assessment evidence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from fdai.core.framework_assessment.models import (
    FrameworkEvidenceReceipt,
    FrameworkSatisfactionStatus,
)
from fdai.rule_catalog.schema.framework_assessment import (
    FrameworkAssessmentCatalog,
    FrameworkEvidenceRole,
    FrameworkProcessPhase,
)
from fdai.shared.providers.framework_assessment import (
    FrameworkObservationRequest,
    FrameworkProviderObservation,
)


class WafExternalSource(StrEnum):
    WELL_ARCHITECTED_REVIEW = "well_architected_review"
    AZURE_ADVISOR = "azure_advisor"
    DEFENDER_SECURE_SCORE = "defender_secure_score"


@dataclass(frozen=True, slots=True)
class WafExternalAssessmentArtifact:
    source: WafExternalSource
    source_identity: str
    scope_digest: str
    control_ids: tuple[str, ...]
    observed_at: datetime
    recorded_at: datetime
    evidence_digest: str
    inventory_generation: str
    complete: bool
    truncated: bool
    conflicting: bool
    synthetic: bool
    provider_error: str | None = None

    def __post_init__(self) -> None:
        if not self.source_identity.strip() or not self.inventory_generation.strip():
            raise ValueError("WAF external artifact requires source and inventory identities")
        if not self.control_ids or self.control_ids != tuple(sorted(set(self.control_ids))):
            raise ValueError(
                "WAF external artifact controls MUST be non-empty, unique, and ordered"
            )
        if self.observed_at.tzinfo is None or self.recorded_at.tzinfo is None:
            raise ValueError("WAF external artifact timestamps MUST be timezone-aware")
        if self.recorded_at < self.observed_at:
            raise ValueError("WAF external artifact recorded_at MUST follow observed_at")


class AzureFrameworkEvidenceAdapter:
    """Convert exact Azure observations into catalog-bound decisive receipts."""

    def __init__(self, catalog: FrameworkAssessmentCatalog) -> None:
        self._catalog = catalog

    def to_receipts(
        self,
        request: FrameworkObservationRequest,
        observations: tuple[FrameworkProviderObservation, ...],
    ) -> tuple[FrameworkEvidenceReceipt, ...]:
        if (
            request.framework_id != self._catalog.framework_id
            or request.catalog_digest != self._catalog.catalog_digest
        ):
            raise ValueError("Azure framework observation request does not match the catalog")
        if len(observations) > request.maximum_observations:
            raise ValueError("Azure framework observations exceed the request bound")
        control_by_id = {item.control_id: item for item in self._catalog.controls}
        receipts: list[FrameworkEvidenceReceipt] = []
        for observation in observations:
            control = control_by_id.get(observation.control_id)
            if control is None or observation.control_id not in request.control_ids:
                raise ValueError("Azure framework observation references an out-of-scope control")
            matches = tuple(
                item
                for item in control.evidence
                if item.source_ref == observation.requirement_ref
                and item.kind.value == observation.evidence_kind
            )
            if len(matches) != 1:
                raise ValueError(
                    "Azure framework observation does not resolve one evidence contract"
                )
            requirement = matches[0]
            if observation.producer != requirement.authoritative_producer:
                raise ValueError("Azure framework observation producer is not authoritative")
            receipts.append(
                FrameworkEvidenceReceipt(
                    framework_id=self._catalog.framework_id,
                    control_id=observation.control_id,
                    requirement_id=requirement.requirement_id,
                    evidence_ref=observation.evidence_ref,
                    evidence_kind=observation.evidence_kind,
                    producer=observation.producer,
                    source_identity=observation.source_identity,
                    scope_digest=request.scope_digest,
                    observed_at=observation.observed_at,
                    recorded_at=observation.recorded_at,
                    evidence_digest=observation.evidence_digest,
                    freshness_ceiling_seconds=requirement.freshness_ceiling_seconds,
                    complete=observation.complete,
                    truncated=observation.truncated,
                    conflicting=observation.conflicting,
                    synthetic=observation.synthetic,
                    provider_error=observation.provider_error,
                    outcome=FrameworkSatisfactionStatus(observation.outcome.value),
                    evidence_role=requirement.evidence_role,
                    process_phase=requirement.process_phase,
                    inventory_generation=request.inventory_generation,
                    hierarchy_generation=request.hierarchy_generation,
                )
            )
        keys = tuple((item.control_id, item.requirement_id, item.evidence_ref) for item in receipts)
        if len(keys) != len(set(keys)):
            raise ValueError("Azure framework observations contain duplicate evidence")
        return tuple(sorted(receipts, key=lambda item: (item.control_id, item.requirement_id)))


class AzureWafSupportingEvidenceAdapter:
    """Preserve external WAF limitations without granting satisfaction authority."""

    def __init__(self, catalog: FrameworkAssessmentCatalog) -> None:
        if catalog.framework_id != "azure-waf":
            raise ValueError("external WAF evidence requires the azure-waf catalog")
        self._control_ids = {item.control_id for item in catalog.controls}

    def to_receipts(
        self,
        artifact: WafExternalAssessmentArtifact,
    ) -> tuple[FrameworkEvidenceReceipt, ...]:
        if not set(artifact.control_ids).issubset(self._control_ids):
            raise ValueError("external WAF artifact references an unknown control")
        return tuple(
            FrameworkEvidenceReceipt(
                framework_id="azure-waf",
                control_id=control_id,
                requirement_id=f"supporting:{artifact.source.value}",
                evidence_ref=f"evidence://supporting/{artifact.source.value}/{control_id}",
                evidence_kind=artifact.source.value,
                producer=f"azure-{artifact.source.value.replace('_', '-')}",
                source_identity=artifact.source_identity,
                scope_digest=artifact.scope_digest,
                observed_at=artifact.observed_at,
                recorded_at=artifact.recorded_at,
                evidence_digest=artifact.evidence_digest,
                freshness_ceiling_seconds=86_400,
                complete=artifact.complete,
                truncated=artifact.truncated,
                conflicting=artifact.conflicting,
                synthetic=artifact.synthetic,
                provider_error=artifact.provider_error,
                outcome=FrameworkSatisfactionStatus.UNKNOWN,
                evidence_role=FrameworkEvidenceRole.SUPPORTING_ONLY,
                process_phase=FrameworkProcessPhase.NONE,
                inventory_generation=artifact.inventory_generation,
            )
            for control_id in artifact.control_ids
        )


__all__ = [
    "AzureFrameworkEvidenceAdapter",
    "AzureWafSupportingEvidenceAdapter",
    "WafExternalAssessmentArtifact",
    "WafExternalSource",
]
