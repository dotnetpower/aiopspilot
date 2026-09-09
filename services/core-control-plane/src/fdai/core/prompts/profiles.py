"""Exact prompt-profile contracts and fail-closed selection budgets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import StrEnum

from fdai.core.prompts.types import ComposedPrompt, LayerRef, PromptArtifact, PromptLayer

_CHARS_PER_TOKEN = 4


class PromptProfileMode(StrEnum):
    """Lifecycle state for one exact prompt composition."""

    ACTIVE = "active"
    SHADOW = "shadow"


@dataclass(frozen=True, slots=True)
class PromptArtifactRef:
    """Exact immutable artifact selected by a prompt profile."""

    id: str
    version: int
    layer: PromptLayer


@dataclass(frozen=True, slots=True)
class PromptProfile:
    """One exact root-and-pack composition with bounded model input."""

    id: str
    version: int
    capability_id: str
    mode: PromptProfileMode
    root: PromptArtifactRef
    packs: tuple[PromptArtifactRef, ...]
    system_token_budget: int
    request_token_budget: int
    reserved_output_tokens: int
    promotion_evidence: tuple[str, ...]
    provenance_source: str

    def __post_init__(self) -> None:
        if self.request_token_budget <= self.system_token_budget:
            raise ValueError("prompt profile request budget MUST exceed its system budget")
        if self.reserved_output_tokens >= self.request_token_budget:
            raise ValueError("prompt profile reserved output MUST be below its request budget")
        if len({(ref.id, ref.version, ref.layer) for ref in self.packs}) != len(self.packs):
            raise ValueError("prompt profile pack refs MUST be unique")

    @property
    def digest(self) -> str:
        """Return a content digest for selection replay and rollback."""

        payload = {
            "capability_id": self.capability_id,
            "id": self.id,
            "mode": self.mode.value,
            "packs": [
                {"id": ref.id, "layer": ref.layer.value, "version": ref.version}
                for ref in self.packs
            ],
            "promotion_evidence": list(self.promotion_evidence),
            "provenance_source": self.provenance_source,
            "request_token_budget": self.request_token_budget,
            "reserved_output_tokens": self.reserved_output_tokens,
            "root": {
                "id": self.root.id,
                "layer": self.root.layer.value,
                "version": self.root.version,
            },
            "system_token_budget": self.system_token_budget,
            "version": self.version,
        }
        encoded = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
        return "sha256:" + hashlib.sha256(encoded.encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class PromptSelection:
    """Resolved profile and exact artifacts for one composition."""

    root: PromptArtifact
    packs: tuple[PromptArtifact, ...]
    profile: PromptProfile | None = None


class PromptBudgetExceededError(ValueError):
    """The selected prompt exceeded its reviewed profile budget."""

    def __init__(self, *, profile_id: str, estimate: int, budget: int) -> None:
        self.profile_id = profile_id
        self.estimate = estimate
        self.budget = budget
        super().__init__(
            f"prompt profile {profile_id!r} exceeds system token budget ({estimate} > {budget})"
        )


def compose_static_selection(selection: PromptSelection) -> ComposedPrompt:
    """Compose catalog-only layers without runtime memory, tools, or skills."""

    artifacts = (selection.root, *selection.packs)
    system_text = "\n\n".join(artifact.body for artifact in artifacts)
    token_estimate = max(1, (len(system_text) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN)
    profile = selection.profile
    if profile is not None and token_estimate > profile.system_token_budget:
        raise PromptBudgetExceededError(
            profile_id=profile.id,
            estimate=token_estimate,
            budget=profile.system_token_budget,
        )
    return ComposedPrompt(
        system_text=system_text,
        layer_manifest=tuple(
            LayerRef(
                id=artifact.id,
                version=artifact.version,
                layer=artifact.layer,
                token_estimate=max(
                    1,
                    (len(artifact.body) + _CHARS_PER_TOKEN - 1) // _CHARS_PER_TOKEN,
                ),
            )
            for artifact in artifacts
        ),
        token_estimate=token_estimate,
        profile_id=profile.id if profile is not None else None,
        profile_version=profile.version if profile is not None else None,
        profile_digest=profile.digest if profile is not None else None,
        system_token_budget=profile.system_token_budget if profile is not None else None,
        request_token_budget=profile.request_token_budget if profile is not None else None,
        reserved_output_tokens=profile.reserved_output_tokens if profile is not None else None,
    )


__all__ = [
    "compose_static_selection",
    "PromptArtifactRef",
    "PromptBudgetExceededError",
    "PromptProfile",
    "PromptProfileMode",
    "PromptSelection",
]
