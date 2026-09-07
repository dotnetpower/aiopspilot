"""Small model boundary for social versus operational conversation routing."""

from __future__ import annotations

import asyncio
import logging
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, Any, Literal, Protocol, cast

from fdai_service_contracts.ontology_query import QueryContract, canonical_json, content_digest
from fdai_service_contracts.semantic_judgment import (
    SemanticDirectResponseDraft,
    SemanticJudgmentProposal,
    SemanticTarget,
    is_polite_korean_answer,
)
from fdai_service_contracts.semantic_turn import SemanticConversationModelTier
from pydantic import Field, ValidationError, model_validator

from .model_observation import ConversationModelObservation, ConversationModelResponse
from .semantic_target_identity import runtime_target_spans

_MAX_UTTERANCE_CHARS = 32_000
_MAX_CONTEXT_ITEMS = 4
_MAX_CONTEXT_CHARS = 4_000
_MAX_PROFILE_BYTES = 16_384
_MAX_SCHEMA_ATTEMPTS = 2
_ROUTE_PROMOTION_CONFIDENCE = 0.9
_OPERATIONAL_ROUTE_PROMOTION_CONFIDENCE = 0.75
_INVENTORY_FACETS = frozenset(
    {"resource_inventory", "subscription", "complete_content", "download"}
)
_RESOURCE_COLLECTION_FACETS = frozenset({"current_state", "list", "resource_collection"})
_SUBSCRIPTION_SCOPE_FACETS = frozenset({"subscription"})
_SUBSCRIPTION_SERVICE_HEALTH_FACETS = frozenset({"service_health"})
_RESOURCE_COLLECTION_FACET_ALIASES = {
    "resource_name_filter": "name_filter",
    "resource_state_filter": "current_state",
}
_CONFIGURATION_FACETS = frozenset(
    {
        "before_after",
        "capacity_units",
        "configuration_changes",
        "default_recent_window",
        "historical_coverage",
        "last_hour",
        "potential_issues",
        "tpm",
    }
)
_GATEWAY_FACETS = frozenset(
    {
        "apim",
        "application_gateway",
        "backend",
        "backend_connect_time",
        "backend_response_code",
        "before_after",
        "configuration_changes",
        "first_byte_time",
        "gateway_response_code",
        "gpt",
        "http_status",
        "last_byte_time",
        "last_hour",
        "latency",
        "status_429",
        "status_500",
        "status_503",
        "topology",
        "total_time",
        "default_recent_window",
    }
)
_GATEWAY_FACET_ALIASES = {
    "api_management": "apim",
    "api_management_issue": "apim",
    "gpt_family": "gpt",
    "gpt_resource_issue": "gpt",
    "gpt_service": "gpt",
    "gpt_version": "gpt",
    "http_429": "status_429",
    "http_500": "status_500",
    "http_503": "status_503",
    "resource_configuration_changes": "configuration_changes",
}
_ONE_HOUR_EXPRESSIONS = frozenset(
    {
        "last hour",
        "past hour",
        "previous hour",
        "the last hour",
        "the past hour",
        "the previous hour",
        "지난 1시간",
        "지난 한 시간",
        "최근 1시간",
        "최근 한 시간",
    }
)
_GENERIC_OPERATIONAL_TARGETS = frozenset(
    {
        "api management",
        "api management service",
        "api",
        "apim",
        "apim gateway",
        "apim service",
        "application gateway",
        "appgw",
        "azure api management",
        "azure api management gateway",
        "azure api management service",
        "azure application gateway",
        "backend",
        "backend instance",
        "backend service",
        "deployment",
        "gateway",
        "gpt",
        "gpt deployment",
        "gpt model",
        "gpt resource",
        "gpt resources",
        "gpt service",
        "model",
        "selected deployment",
        "selected gateway",
        "this deployment",
        "this gateway",
        "게이트웨이",
        "모델",
        "배포",
        "백엔드",
        "애플리케이션 게이트웨이",
    }
)
_GENERIC_OPERATIONAL_TARGET_PATTERN = re.compile(
    r"(?:(?:gpt\s*)?\d+(?:\.\d+)+(?:\s+(?:deployment|model|resource|service))?|"
    r"(?:http\s*)?[1-5]\d\d)"
)
_LOGGER = logging.getLogger(__name__)
Digest = Annotated[str, Field(pattern=r"^sha256:[a-f0-9]{64}$")]
_GENERAL_LINK_LIKE_TEXT = re.compile(
    r"\b[a-z0-9](?:[a-z0-9-]{0,62})\.[a-z]{2,63}\b",
    re.IGNORECASE,
)
_TECHNICAL_DOTTED_IDENTIFIERS = frozenset({"asp.net", "node.js"})
_GENERAL_SCOPE_NOUN = re.compile(
    r"\b(?:subscriptions?|resource\s+groups?)\b|(?:구독|리소스\s*그룹)",
    re.IGNORECASE,
)
_GENERAL_SCOPE_ASSERTION = re.compile(
    r"\b(?:contains?|has|holds?|stores?|reports?|shows?|includes?|runs?|"
    r"is\s+running|are\s+running|hosts?|manages?)\b|"
    r"(?:있습니다|보유|포함|처리|제공|저장|실행\s*중|호스팅|관리)",
    re.IGNORECASE,
)
_GENERAL_SCOPE_OBJECT = re.compile(
    r"\b(?:resources?|records?|items?|services?)\b|(?:리소스|레코드|항목|서비스)",
    re.IGNORECASE,
)
_SUBSCRIPTION_NAME_AFTER = re.compile(
    r"(?i)\bsubscription\s+(?:named\s+)?([A-Za-z0-9][A-Za-z0-9_.-]*)\b"
)
_EXPLICIT_NAMED_SUBSCRIPTION = re.compile(
    r"(?i)\bsubscription\s+named\s+[A-Za-z0-9][A-Za-z0-9_.-]*\b"
)
_SUBSCRIPTION_NAME_BEFORE_KOREAN = re.compile(
    r"(?i)(?<!\S)([^\s,.;:!?]{1,64})\s+구독(?:의|은|는|이|가|을|를)?"
)
_SUBSCRIPTION_NAME_BEFORE = re.compile(
    r"(?i)\b(?:the\s+)?([A-Za-z0-9][A-Za-z0-9_.-]*)\s+subscription\b"
)
_GENERIC_SUBSCRIPTION_WORDS = frozenset(
    {
        "azure",
        "authorized",
        "configured",
        "current",
        "details",
        "health",
        "identity",
        "information",
        "name",
        "scope",
        "service",
        "state",
        "status",
        "있는",
    }
)
_GENERIC_SUBSCRIPTION_SCOPE_FILTERS = frozenset(
    {"subscription", "the subscription", "current subscription", "구독", "현재 구독"}
)
_GENERAL_FORBIDDEN_CLAIMS = (
    re.compile(
        r"\b(?:i|we|fdai)\s+(?:have\s+)?"
        r"(?:verified|confirmed|observed|checked|queried|measured|executed|restarted|"
        r"deployed|changed|approved)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:your|current|live|production)\s+"
        r"(?:environment|deployment|resource|system|cluster|service|gateway|backend|model|"
        r"api|database|pod|container|workload|application|endpoint|queue|job|vm|server|"
        r"subscription|resource\s+group)s?\s+"
        r"(?:is|are|was|were|has|have|runs?|uses?|shows?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:the|your|this|our)\s+"
        r"(?:environment|deployment|resource|system|cluster|service|gateway|backend|model|"
        r"api|database|pod|container|workload|application|endpoint|queue|job|vm|server)s?\s+"
        r"(?:is|are|was|were|has\s+been|have\s+been)\s+"
        r"(?:currently\s+)?"
        r"(?:healthy|unhealthy|running|degraded|available|unavailable|restarted|deployed|"
        r"changed|approved|executed)(?:\s+successfully)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:it|this|that|the\s+(?:environment|deployment|resource|system|cluster|service|"
        r"gateway|backend|model|api|database|pod|container|workload|application|endpoint|"
        r"queue|job|vm|server))"
        r"\s+(?:is|are|was|were|looks?|seems?)\s+"
        r"(?:healthy|unhealthy|running|degraded|available|unavailable|normal)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:it|this|that)\s+"
        r"(?:restarted|deployed|changed|approved|executed|scaled|stopped|started)"
        r"(?:\s+successfully)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:the|your|our|this)\s+"
        r"(?:environment|deployment|resource|system|cluster|service|gateway|backend|model|"
        r"api|database|pod|container|workload|application|endpoint|queue|job|vm|server)s?"
        r"\s+(?:restarted|deployed|changed|approved|executed|scaled|stopped|started)"
        r"(?:\s+successfully)?\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:the|your|our|this)\s+(?:(?:production|live|current)\s+)?"
        r"(?:environment|deployment|resource|system|cluster|service|gateway|backend|model|"
        r"api|database|pod|container|workload|application|endpoint|queue|job|vm|server|"
        r"subscription|resource\s+group)s?"
        r"\s+(?:currently\s+)?"
        r"(?:contains?|has|holds?|stores?|reports?|shows?|serves?|processes?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:subscription|resource\s+group)s?\s+"
        r"(?:contains?|has|holds?|stores?|reports?|shows?)\s+\d+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:the\s+)?(?:[a-z0-9_.-]+\s+){1,6}(?:subscription|resource\s+group)s?\s+"
        r"(?:contains?|has|holds?|stores?|reports?|shows?)\b.{0,48}"
        r"(?:resources?|records?|items?|services?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:subscription|resource\s+group)s?\s+\S{1,64}\s+"
        r"(?:contains?|has|holds?|stores?|reports?|shows?)\s+\d+\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:subscription|resource\s+group)s?\s+"
        r"(?:(?!(?:contains?|has|holds?|stores?|reports?|shows?)\b)\S+\s+){1,6}"
        r"(?:contains?|has|holds?|stores?|reports?|shows?)\b.{0,48}"
        r"(?:resources?|records?|items?|services?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:^|[.!?]\s+)(?:please\s+)?"
        r"(?:restart|deploy|change|approve|execute|delete|scale|stop|start)\s+"
        r"(?:the\s+)?(?:current|live|production)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:restart|deploy|change|approve|execute|delete|scale|stop|start)\b"
        r".{0,48}\b(?:production|live)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:our|your|the|this)\s+(?:(?:production|live)\s+)?"
        r"(?:environment|deployment|resource|system|cluster|service|gateway|backend|model|"
        r"api|database|pod|container|workload|application|endpoint|queue|job|vm|server)s?\b"
        r".{0,40}\b(?:currently\s+)?(?:is|are|was|were|runs?|ran)\b"
        r".{0,40}\b(?:production|live|healthy|unhealthy|running|degraded)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:FDAI가|제가|저희가).{0,16}"
        r"(?:확인|검증|관찰|조회|측정|실행|재시작|배포|변경|승인)"
        r"(?:했|하였|했습니다|완료)",
    ),
    re.compile(
        r"(?:현재|실제|운영|프로덕션)\s*"
        r"(?:환경|배포|리소스|시스템|클러스터|서비스|게이트웨이|백엔드|모델|API|"
        r"데이터베이스|파드|컨테이너|워크로드|애플리케이션|엔드포인트|큐|작업|VM|서버)"
        r"(?:은|는|이|가).{0,24}"
        r"(?:정상|비정상|건강|실행 중|배포되|확인되|관찰되|측정되)",
    ),
    re.compile(
        r"(?:현재|실제|운영|프로덕션).{0,24}"
        r"(?:재시작|배포|변경|승인|실행|삭제|확장|중지|시작)"
        r"(?:하세요|하십시오|해 주세요|했습니다|됐|되었습니다)",
    ),
    re.compile(
        r"(?:환경|배포|리소스|시스템|클러스터|서비스|게이트웨이|백엔드|모델|API|"
        r"데이터베이스|파드|컨테이너|워크로드|애플리케이션|엔드포인트|큐|작업|VM|서버)"
        r"(?:은|는|이|가)\s*(?:현재\s*)?"
        r"(?:(?:정상|비정상|건강함|실행 중|사용 가능)(?:입니다|이에요)|"
        r"(?:재시작|배포|변경|승인|실행)(?:됐습니다|되었습니다|했습니다))",
    ),
    re.compile(
        r"(?:환경|배포|리소스|시스템|클러스터|서비스|게이트웨이|백엔드|모델|API|"
        r"데이터베이스|파드|컨테이너|워크로드|애플리케이션|엔드포인트|큐|작업|VM|서버)"
        r"(?:은|는|이|가).{0,32}"
        r"(?:운영\s*환경|프로덕션).{0,24}"
        r"(?:정상|비정상|건강|실행 중|재시작|배포|변경|승인|실행)",
    ),
    re.compile(
        r"(?:프로덕션|운영\s*환경)(?:은|는|이|가).{0,16}"
        r"(?:정상|비정상|건강|실행 중|재시작|배포|변경|승인|실행)",
    ),
    re.compile(
        r"(?:현재|실제|프로덕션|운영\s*환경|해당).{0,32}"
        r"(?:환경|배포|리소스|시스템|클러스터|서비스|게이트웨이|백엔드|모델|API|"
        r"데이터베이스|파드|컨테이너|워크로드|애플리케이션|엔드포인트|큐|작업|VM|서버|"
        r"구독|리소스\s*그룹)"
        r".{0,32}(?:있습니다|보유|포함|처리|제공|저장)",
    ),
    re.compile(
        r"(?:구독|리소스\s*그룹)(?:에는|은|는|이|가).{0,24}\d+개.{0,16}"
        r"(?:있습니다|보유|포함|처리|제공|저장)",
    ),
    re.compile(
        r"(?:구독|리소스\s*그룹)\s+\S{1,64}(?:에는|은|는|이|가).{0,24}\d+개"
        r".{0,16}(?:있습니다|보유|포함|처리|제공|저장)",
    ),
    re.compile(
        r"(?:구독|리소스\s*그룹)\s+\S+(?:\s+\S+){0,5}(?:에는|은|는|이|가)"
        r".{0,32}(?:리소스|레코드|항목|서비스).{0,20}"
        r"(?:있습니다|보유|포함|처리|제공|저장)",
    ),
    re.compile(
        r"\S+(?:\s+\S+){0,5}\s+(?:구독|리소스\s*그룹)(?:에는|은|는|이|가)"
        r".{0,32}(?:리소스|레코드|항목|서비스).{0,20}"
        r"(?:있습니다|보유|포함|처리|제공|저장)",
    ),
)


class SocialAct(StrEnum):
    """Optional social meaning that never grants operational authority."""

    NONE = "none"
    GREETING = "greeting"
    ACKNOWLEDGEMENT = "acknowledgement"
    THANKS = "thanks"
    FAREWELL = "farewell"
    SELF_INTRODUCTION = "self_introduction"


DIRECT_SOCIAL_ACTS = frozenset(
    {
        SocialAct.GREETING,
        SocialAct.THANKS,
        SocialAct.FAREWELL,
        SocialAct.SELF_INTRODUCTION,
    }
)
SOCIAL_NARRATOR_CAPABILITY_IDS = MappingProxyType(
    {
        SocialAct.GREETING: "conversation.social-narrator.greeting",
        SocialAct.THANKS: "conversation.social-narrator.thanks",
        SocialAct.FAREWELL: "conversation.social-narrator.farewell",
        SocialAct.SELF_INTRODUCTION: "conversation.social-narrator.self_introduction",
    }
)
if frozenset(SOCIAL_NARRATOR_CAPABILITY_IDS) != DIRECT_SOCIAL_ACTS:
    raise RuntimeError("every direct social act requires one reviewed narrator prompt mapping")


class OperationalSignal(StrEnum):
    """Whether the complete turn requires operational semantic planning."""

    NONE = "none"
    EXPLICIT = "explicit"
    CONTEXTUAL = "contextual"
    MIXED = "mixed"


class ContextDependency(StrEnum):
    """Whether interpreting the turn depends on prior operational state."""

    NONE = "none"
    SOCIAL_CONTINUITY = "social_continuity"
    ACTIVE_THREAD = "active_thread"
    PENDING_DECISION = "pending_decision"
    AMBIGUOUS = "ambiguous"


class GeneralKnowledgeSignal(StrEnum):
    """Whether the turn explicitly requests environment-independent knowledge."""

    NONE = "none"
    EXPLICIT = "explicit"


class GeneralKnowledgeDraft(QueryContract):
    """One bounded no-authority answer authored with the routing decision."""

    locale: Literal["en", "ko"]
    answer: Annotated[str, Field(min_length=1, max_length=400)]
    profile_digest: Digest
    execution_authority: Literal[False] = False

    @model_validator(mode="after")
    def _answer_is_usable(self) -> GeneralKnowledgeDraft:
        if self.answer != self.answer.strip():
            raise ValueError("general knowledge answer MUST be trimmed")
        if (
            "://" in self.answer
            or re.search(r"\[[^\]]+\]\([^)]+\)", self.answer)
            or _general_answer_contains_bare_domain(self.answer)
        ):
            raise ValueError("general knowledge answer MUST NOT contain links")
        if self.locale == "ko" and not is_polite_korean_answer(self.answer):
            raise ValueError("Korean general knowledge answer MUST use polite honorific endings")
        if _general_answer_contains_scope_assertion(self.answer) or any(
            pattern.search(self.answer) for pattern in _GENERAL_FORBIDDEN_CLAIMS
        ):
            raise ValueError("general knowledge answer MUST NOT claim operational observation")
        return self


def _general_answer_contains_scope_assertion(answer: str) -> bool:
    clauses = re.split(r"(?:[!?。！？;]+|\.(?=\s|$))", answer)
    return any(
        _GENERAL_SCOPE_NOUN.search(clause)
        and _GENERAL_SCOPE_ASSERTION.search(clause)
        and _GENERAL_SCOPE_OBJECT.search(clause)
        for clause in clauses
    )


def _general_answer_contains_bare_domain(answer: str) -> bool:
    for match in _GENERAL_LINK_LIKE_TEXT.finditer(answer):
        token = match.group(0).casefold()
        quoted = (
            match.start() > 0
            and match.end() < len(answer)
            and answer[match.start() - 1] == "`"
            and answer[match.end()] == "`"
        )
        if token in _TECHNICAL_DOTTED_IDENTIFIERS or quoted:
            continue
        return True
    return False


class OperationalPreflightFamily(StrEnum):
    """Small reviewed operational family set that can skip full judgment."""

    NONE = "none"
    INVENTORY_DOCUMENT = "inventory_document"
    RESOURCE_COLLECTION = "resource_collection"
    RESOURCE_CURRENT_STATE = "resource_current_state"
    SUBSCRIPTION_SCOPE_IDENTITY = "subscription_scope_identity"
    SUBSCRIPTION_SERVICE_HEALTH = "subscription_service_health"
    RESOURCE_CONFIGURATION_CHANGES = "resource_configuration_changes"
    GATEWAY_DIAGNOSTIC_EVIDENCE = "gateway_diagnostic_evidence"


class OperationalWindowMode(StrEnum):
    """Typed temporal posture for one reviewed operational preflight family."""

    NONE = "none"
    PAST_HOUR = "past_hour"
    SERVER_RECENT_DEFAULT = "server_recent_default"


class ConversationPreflightProposal(QueryContract):
    """Untrusted compact route proposal without user-facing response prose."""

    schema_version: Literal["1.0.0"] = "1.0.0"
    social_act: SocialAct
    operational_signal: OperationalSignal
    context_dependency: ContextDependency
    knowledge_signal: GeneralKnowledgeSignal = GeneralKnowledgeSignal.NONE
    general_answer: GeneralKnowledgeDraft | None = None
    operational_family: OperationalPreflightFamily = OperationalPreflightFamily.NONE
    operational_window: OperationalWindowMode = OperationalWindowMode.NONE
    operational_targets: Annotated[tuple[SemanticTarget, ...], Field(max_length=4)] = ()
    operational_facets: Annotated[tuple[str, ...], Field(max_length=24)] = ()
    confidence: Annotated[float, Field(ge=0.0, le=1.0)]
    authority: Literal["candidate_only"] = "candidate_only"
    execution_authority: Literal[False] = False

    @model_validator(mode="after")
    def _route_is_consistent(self) -> ConversationPreflightProposal:
        if not math.isfinite(self.confidence):
            raise ValueError("conversation preflight confidence MUST be finite")
        known_operational = self.operational_family is not OperationalPreflightFamily.NONE
        if known_operational != bool(self.operational_targets or self.operational_facets):
            raise ValueError("known operational preflight family requires typed details")
        if known_operational and self.operational_signal is not OperationalSignal.EXPLICIT:
            raise ValueError("operational preflight family requires an explicit operational signal")
        if not known_operational and self.operational_window is not OperationalWindowMode.NONE:
            raise ValueError("operational preflight window requires a known operational family")
        if len(self.operational_facets) != len(set(self.operational_facets)):
            raise ValueError("operational preflight facets MUST be unique")
        pure_general = (
            self.social_act is SocialAct.NONE
            and self.knowledge_signal is GeneralKnowledgeSignal.EXPLICIT
            and self.operational_signal is OperationalSignal.NONE
            and self.context_dependency is ContextDependency.NONE
        )
        if pure_general != (self.general_answer is not None):
            raise ValueError("pure general knowledge requires exactly one bounded answer")
        return self


class ConversationPreflightModel(Protocol):
    """Propose one compact no-authority conversation route."""

    def preflight(
        self,
        *,
        utterance: str,
        context: tuple[str, ...],
        locale: str,
        direct_response_profile: Mapping[str, Any],
        direct_response_profile_digest: str,
        schema_repair: tuple[dict[str, str], ...],
    ) -> Mapping[str, Any] | ConversationModelResponse | None: ...


class CancellableConversationPreflightModel(ConversationPreflightModel, Protocol):
    """Preflight provider that explicitly supports cancellation propagation."""

    def preflight(
        self,
        *,
        utterance: str,
        context: tuple[str, ...],
        locale: str,
        direct_response_profile: Mapping[str, Any],
        direct_response_profile_digest: str,
        schema_repair: tuple[dict[str, str], ...],
        cancelled: asyncio.Event | None = None,
    ) -> Mapping[str, Any] | ConversationModelResponse | None: ...


class SocialResponseNarratorModel(Protocol):
    """Author one bounded response after social routing is validated."""

    def narrate_social(
        self,
        *,
        utterance: str,
        locale: str,
        social_act: str,
        continued: bool,
        direct_response_profile: Mapping[str, Any],
        direct_response_profile_digest: str,
    ) -> Mapping[str, Any] | ConversationModelResponse | None: ...


@dataclass(frozen=True, slots=True)
class ConversationPreflightBinding:
    """One configured T1 preflight model and its prompt provenance."""

    model: ConversationPreflightModel
    model_config_digest: str
    prompt_digest: str
    supports_cancellation: bool = False


@dataclass(frozen=True, slots=True)
class SocialResponseNarratorBinding:
    """One separately configured social response model."""

    model: SocialResponseNarratorModel
    model_config_digest: str
    prompt_digest: str


@dataclass(frozen=True, slots=True)
class ConversationPreflightResult:
    """One optional validated preflight proposal and measured observations."""

    proposal: ConversationPreflightProposal | None
    observations: tuple[ConversationModelObservation, ...] = ()
    attempted: bool = False
    failure_kind: Literal["provider_unavailable", "malformed"] | None = None
    input_digest: str | None = None
    proposal_digest: str | None = None
    model_config_digest: str | None = None
    prompt_digest: str | None = None
    direct_response_profile_digest: str | None = None


@dataclass(frozen=True, slots=True)
class SocialResponseNarratorResult:
    """One validated social response or a bounded failure."""

    draft: SemanticDirectResponseDraft | None
    observations: tuple[ConversationModelObservation, ...] = ()
    attempted: bool = False


class ConversationPreflightBoundary:
    """Run one compact T1 attempt and fail open only to full semantic judgment."""

    def __init__(
        self,
        *,
        binding: ConversationPreflightBinding | None,
        t2_binding: ConversationPreflightBinding | None = None,
        narrator: SocialResponseNarratorBinding | None = None,
    ) -> None:
        self._binding = binding
        self._t2_binding = t2_binding
        self._narrator = narrator

    def classify(
        self,
        *,
        utterance: str,
        context: Sequence[str],
        locale: str,
        direct_response_profile: Mapping[str, Any],
        cancelled: asyncio.Event | None = None,
        conversation_model_tier: SemanticConversationModelTier | None = None,
    ) -> ConversationPreflightResult:
        """Return a validated candidate or no proposal for full-path continuation."""

        binding = (
            self._t2_binding
            if conversation_model_tier is SemanticConversationModelTier.T2
            else self._binding
        )
        if binding is None or not utterance.strip() or len(utterance) > _MAX_UTTERANCE_CHARS:
            return ConversationPreflightResult(proposal=None)
        try:
            bounded_context = _bounded_context(context)
            bounded_profile = _bounded_profile(direct_response_profile)
        except (TypeError, ValueError):
            return ConversationPreflightResult(proposal=None)
        response_locale = "ko" if locale.casefold().startswith("ko") else "en"
        profile_digest = content_digest(bounded_profile)
        observations: list[ConversationModelObservation] = []
        schema_repair: tuple[dict[str, str], ...] = ()
        for attempt in range(_MAX_SCHEMA_ATTEMPTS):
            try:
                if binding.supports_cancellation:
                    response = cast(
                        CancellableConversationPreflightModel,
                        binding.model,
                    ).preflight(
                        utterance=utterance,
                        context=bounded_context,
                        locale=response_locale,
                        direct_response_profile=bounded_profile,
                        direct_response_profile_digest=profile_digest,
                        schema_repair=schema_repair,
                        cancelled=cancelled,
                    )
                else:
                    response = binding.model.preflight(
                        utterance=utterance,
                        context=bounded_context,
                        locale=response_locale,
                        direct_response_profile=bounded_profile,
                        direct_response_profile_digest=profile_digest,
                        schema_repair=schema_repair,
                    )
            except Exception as exc:  # noqa: BLE001 - full judgment remains the safe fallback
                _LOGGER.warning(
                    "conversation_preflight_model_failed",
                    extra={"failure_type": type(exc).__name__},
                )
                return ConversationPreflightResult(
                    proposal=None,
                    observations=tuple(observations),
                    attempted=True,
                    failure_kind="provider_unavailable",
                )
            if response is None:
                return ConversationPreflightResult(
                    proposal=None,
                    observations=tuple(observations),
                    attempted=True,
                    failure_kind="provider_unavailable",
                )
            raw: Mapping[str, Any]
            if isinstance(response, ConversationModelResponse):
                raw = response.proposal
                observations.append(response.observation)
            else:
                raw = response
            try:
                proposal = ConversationPreflightProposal.model_validate(raw)
            except (TypeError, ValueError, ValidationError) as exc:
                if attempt + 1 < _MAX_SCHEMA_ATTEMPTS:
                    schema_repair = (_repair_instruction(exc),)
                    continue
                return ConversationPreflightResult(
                    proposal=None,
                    observations=tuple(observations),
                    attempted=True,
                    failure_kind="malformed",
                )
            return ConversationPreflightResult(
                proposal=proposal,
                observations=tuple(observations),
                attempted=True,
                input_digest=_preflight_input_digest(utterance),
                proposal_digest=content_digest(proposal.model_dump(mode="json")),
                model_config_digest=binding.model_config_digest,
                prompt_digest=binding.prompt_digest,
                direct_response_profile_digest=profile_digest,
            )
        raise RuntimeError("conversation preflight attempt bound is unreachable")

    def narrate_social(
        self,
        *,
        utterance: str,
        locale: str,
        social_act: SocialAct,
        continued: bool,
        direct_response_profile: Mapping[str, Any],
    ) -> SocialResponseNarratorResult:
        """Author one response without exposing operational context or capabilities."""

        if self._narrator is None:
            return SocialResponseNarratorResult(draft=None)
        response_locale = "ko" if locale.casefold().startswith("ko") else "en"
        try:
            bounded_profile = _bounded_profile(direct_response_profile)
        except (TypeError, ValueError):
            return SocialResponseNarratorResult(draft=None)
        profile_digest = content_digest(bounded_profile)
        try:
            response = self._narrator.model.narrate_social(
                utterance=utterance,
                locale=response_locale,
                social_act=social_act.value,
                continued=continued,
                direct_response_profile=bounded_profile,
                direct_response_profile_digest=profile_digest,
            )
        except Exception as exc:  # noqa: BLE001 - terminal hold is the safe fallback
            _LOGGER.warning(
                "social_response_narrator_failed",
                extra={"failure_type": type(exc).__name__},
            )
            return SocialResponseNarratorResult(draft=None, attempted=True)
        if response is None:
            return SocialResponseNarratorResult(draft=None, attempted=True)
        observation: ConversationModelObservation | None = None
        raw: Mapping[str, Any]
        if isinstance(response, ConversationModelResponse):
            raw = response.proposal
            observation = response.observation
        else:
            raw = response
        try:
            draft = SemanticDirectResponseDraft.model_validate(raw)
            if draft.locale != response_locale or draft.profile_digest != profile_digest:
                raise ValueError("social response narrator binding mismatch")
        except (TypeError, ValueError, ValidationError):
            return SocialResponseNarratorResult(
                draft=None,
                observations=(observation,) if observation is not None else (),
                attempted=True,
            )
        return SocialResponseNarratorResult(
            draft=draft,
            observations=(observation,) if observation is not None else (),
            attempted=True,
        )


def preflight_operational_judgment(
    result: ConversationPreflightResult,
    *,
    utterance: str,
) -> SemanticJudgmentProposal | None:
    """Promote a bounded preflight family to candidate judgment after source checks."""
    proposal = result.proposal
    if proposal is None:
        return _reject_operational_promotion("proposal_absent")
    checks = (
        (result.attempted, "preflight_not_attempted"),
        (result.failure_kind is None, "preflight_failed"),
        (
            proposal.operational_family is not OperationalPreflightFamily.NONE,
            "family_absent",
        ),
        (
            proposal.operational_signal is OperationalSignal.EXPLICIT,
            "signal_not_explicit",
        ),
        (
            proposal.context_dependency is ContextDependency.NONE,
            "context_dependent",
        ),
        (
            proposal.confidence >= _OPERATIONAL_ROUTE_PROMOTION_CONFIDENCE,
            "confidence_below_threshold",
        ),
        (
            result.input_digest == _preflight_input_digest(utterance),
            "input_digest_mismatch",
        ),
        (
            result.proposal_digest == content_digest(proposal.model_dump(mode="json")),
            "proposal_digest_mismatch",
        ),
        (result.model_config_digest is not None, "model_provenance_absent"),
        (result.prompt_digest is not None, "prompt_provenance_absent"),
    )
    for passed, reason in checks:
        if not passed:
            return _reject_operational_promotion(reason)
    exact_runtime_spans = runtime_target_spans(utterance)
    normalized_targets: list[SemanticTarget] = []
    for target in proposal.operational_targets:
        if (
            proposal.operational_family is OperationalPreflightFamily.RESOURCE_CONFIGURATION_CHANGES
            and target.kind == "resource_type_filter"
            and target.value.strip().casefold() in _GENERIC_SUBSCRIPTION_SCOPE_FILTERS
        ):
            continue
        if (
            proposal.operational_family is OperationalPreflightFamily.GATEWAY_DIAGNOSTIC_EVIDENCE
            and target.kind in {"resource", "backend", "model"}
            and operational_target_is_generic(target.value)
        ):
            continue
        if utterance[target.source_start : target.source_end] != target.value:
            source_start = utterance.find(target.value)
            if source_start < 0 or utterance.find(target.value, source_start + 1) >= 0:
                return _reject_operational_promotion("target_not_unique_in_source")
            target = target.model_copy(
                update={
                    "source_start": source_start,
                    "source_end": source_start + len(target.value),
                }
            )
        if target.kind == "time_range":
            if target.canonical_value != "duration.PT1H" or not operational_time_is_past_hour(
                target.value
            ):
                return _reject_operational_promotion("unsupported_time_canonicalization")
        collection_filter = proposal.operational_family in {
            OperationalPreflightFamily.RESOURCE_COLLECTION,
            OperationalPreflightFamily.RESOURCE_CONFIGURATION_CHANGES,
        } and target.kind in {
            "resource_type_filter",
            "resource_state_filter",
            "resource_name_filter",
        }
        if target.kind not in {
            "resource",
            "time_range",
            "backend",
            "model",
            "resource_type_filter",
            "resource_state_filter",
            "resource_name_filter",
        }:
            return _reject_operational_promotion("unsupported_target_kind")
        if collection_filter and target.canonical_value is not None:
            return _reject_operational_promotion("collection_filter_canonicalization_not_allowed")
        if collection_filter and any(
            start <= target.source_start and target.source_end <= end
            for start, end in exact_runtime_spans
        ):
            return _reject_operational_promotion("collection_filter_overlaps_exact_resource")
        if (
            collection_filter
            and target.kind != "resource_state_filter"
            and (
                target.value.casefold().startswith("/subscriptions/")
                or (
                    not any(character.isspace() for character in target.value)
                    and (
                        "-" in target.value
                        or any(character.isdigit() for character in target.value)
                    )
                )
            )
        ):
            return _reject_operational_promotion("collection_filter_looks_like_exact_resource")
        if (
            target.kind != "time_range"
            and not collection_filter
            and not operational_target_is_exact(target.value)
        ):
            return _reject_operational_promotion("generic_target_identity")
        if (
            proposal.operational_family is OperationalPreflightFamily.RESOURCE_CURRENT_STATE
            and target.kind == "resource"
        ):
            target = target.model_copy(
                update={
                    "canonical_value": (
                        "Resource.id"
                        if target.value.casefold().startswith("/subscriptions/")
                        else "Resource.name"
                    )
                }
            )
        normalized_targets.append(target)
    if (
        proposal.operational_family is OperationalPreflightFamily.GATEWAY_DIAGNOSTIC_EVIDENCE
        and not any(target.kind == "resource" for target in normalized_targets)
        and len(exact_runtime_spans) == 1
    ):
        source_start, source_end = exact_runtime_spans[0]
        normalized_targets.append(
            SemanticTarget(
                kind="resource",
                value=utterance[source_start:source_end],
                canonical_value="Resource.name",
                source_start=source_start,
                source_end=source_end,
            )
        )
    primary_intent = {
        OperationalPreflightFamily.INVENTORY_DOCUMENT: "create.document",
        OperationalPreflightFamily.RESOURCE_CONFIGURATION_CHANGES: (
            "query.resource_configuration_changes"
        ),
        OperationalPreflightFamily.GATEWAY_DIAGNOSTIC_EVIDENCE: (
            "query.gateway_diagnostic_evidence"
        ),
        OperationalPreflightFamily.RESOURCE_CURRENT_STATE: "query.resource_current_state",
        OperationalPreflightFamily.SUBSCRIPTION_SCOPE_IDENTITY: (
            "query.subscription_scope_identity"
        ),
        OperationalPreflightFamily.SUBSCRIPTION_SERVICE_HEALTH: (
            "query.subscription_service_health"
        ),
    }.get(proposal.operational_family)
    target_kinds = tuple(target.kind for target in normalized_targets)
    facets = frozenset(
        _RESOURCE_COLLECTION_FACET_ALIASES.get(facet, facet)
        if proposal.operational_family is OperationalPreflightFamily.RESOURCE_COLLECTION
        else facet
        for facet in proposal.operational_facets
    )
    normalized_operational_facets = proposal.operational_facets
    if proposal.operational_family is OperationalPreflightFamily.INVENTORY_DOCUMENT:
        family_valid = (
            not target_kinds
            and {"resource_inventory", "subscription"} <= facets <= _INVENTORY_FACETS
        )
        normalized_operational_facets = (
            "resource_inventory",
            "subscription",
            "complete_content",
            "download",
        )
    elif proposal.operational_family is OperationalPreflightFamily.RESOURCE_COLLECTION:
        has_state_filter = target_kinds.count("resource_state_filter") == 1
        has_name_filter = target_kinds.count("resource_name_filter") == 1
        expected_facets = {"resource_collection", "list"}
        if has_state_filter:
            expected_facets.add("current_state")
        if has_name_filter:
            expected_facets.add("name_filter")
        family_valid = (
            set(target_kinds)
            <= {"resource_type_filter", "resource_state_filter", "resource_name_filter"}
            and target_kinds.count("resource_type_filter") <= 1
            and target_kinds.count("resource_state_filter") <= 1
            and target_kinds.count("resource_name_filter") <= 1
            and len(target_kinds) == len(set(target_kinds))
            and bool(target_kinds)
            and {"resource_collection", "list"} <= facets <= expected_facets
        )
        normalized_operational_facets = tuple(
            facet
            for facet in ("resource_collection", "list", "name_filter", "current_state")
            if facet in expected_facets
        )
        primary_intent = (
            "query.resource_state_inventory" if has_state_filter else "query.contextual_resources"
        )
    elif proposal.operational_family is OperationalPreflightFamily.RESOURCE_CURRENT_STATE:
        family_valid = target_kinds == ("resource",) and facets == {"current_state"}
    elif proposal.operational_family is OperationalPreflightFamily.SUBSCRIPTION_SCOPE_IDENTITY:
        family_valid = (
            not target_kinds
            and facets == _SUBSCRIPTION_SCOPE_FACETS
            and not named_subscription_requested(utterance)
        )
    elif proposal.operational_family is OperationalPreflightFamily.SUBSCRIPTION_SERVICE_HEALTH:
        family_valid = (
            not target_kinds
            and facets == _SUBSCRIPTION_SERVICE_HEALTH_FACETS
            and not named_subscription_requested(utterance)
        )
    elif proposal.operational_family is OperationalPreflightFamily.RESOURCE_CONFIGURATION_CHANGES:
        has_resource = target_kinds.count("resource") == 1
        has_resource_type = target_kinds.count("resource_type_filter") == 1
        has_time = target_kinds.count("time_range") == 1
        configuration_facets = [
            facet for facet in proposal.operational_facets if facet in _CONFIGURATION_FACETS
        ]
        normalized_configuration_facets = frozenset(configuration_facets)
        if (
            has_resource_type
            and not has_time
            and "default_recent_window" not in normalized_configuration_facets
        ):
            configuration_facets.append("default_recent_window")
        normalized_operational_facets = tuple(configuration_facets)
        normalized_configuration_facets = frozenset(configuration_facets)
        family_valid = (
            (
                (
                    has_resource
                    and not has_resource_type
                    and has_time
                    and len(target_kinds) == 2
                    and not next(
                        target.value.casefold().startswith("/subscriptions/")
                        for target in normalized_targets
                        if target.kind == "resource"
                    )
                )
                or (
                    has_resource_type
                    and not has_resource
                    and target_kinds.count("time_range") <= 1
                    and len(target_kinds) == 1 + int(has_time)
                    and (has_time or "default_recent_window" in normalized_configuration_facets)
                )
            )
            and (
                (
                    has_time
                    and proposal.operational_window
                    in {OperationalWindowMode.NONE, OperationalWindowMode.PAST_HOUR}
                )
                or (
                    not has_time
                    and (
                        proposal.operational_window
                        in {OperationalWindowMode.NONE, OperationalWindowMode.SERVER_RECENT_DEFAULT}
                        and "default_recent_window" in normalized_configuration_facets
                    )
                )
            )
            and bool(normalized_configuration_facets - {"default_recent_window", "last_hour"})
        )
    elif proposal.operational_family is OperationalPreflightFamily.GATEWAY_DIAGNOSTIC_EVIDENCE:
        has_time = target_kinds.count("time_range") == 1
        canonical_gateway_facets: list[str] = []
        for facet in proposal.operational_facets:
            canonical_facet = _GATEWAY_FACET_ALIASES.get(facet, facet)
            if (
                canonical_facet in _GATEWAY_FACETS
                and canonical_facet not in canonical_gateway_facets
            ):
                canonical_gateway_facets.append(canonical_facet)
        has_current_error_status = any(
            facet in {"status_429", "status_500", "status_503"}
            for facet in canonical_gateway_facets
        )
        if (
            not has_time
            and (
                proposal.operational_window is OperationalWindowMode.SERVER_RECENT_DEFAULT
                or has_current_error_status
            )
            and "default_recent_window" not in canonical_gateway_facets
        ):
            canonical_gateway_facets.append("default_recent_window")
        has_grounded_gateway_facet = bool(canonical_gateway_facets)
        normalized_operational_facets = tuple(canonical_gateway_facets)
        family_valid = (
            target_kinds.count("resource") == 1
            and target_kinds.count("time_range") <= 1
            and target_kinds.count("backend") <= 1
            and target_kinds.count("model") <= 1
            and target_kinds.count("backend") + target_kinds.count("model") <= 1
            and len(target_kinds) == len(set(target_kinds))
            and (has_time or "default_recent_window" in canonical_gateway_facets)
            and (
                (
                    has_time
                    and proposal.operational_window
                    in {OperationalWindowMode.NONE, OperationalWindowMode.PAST_HOUR}
                )
                or (
                    not has_time
                    and (
                        proposal.operational_window is OperationalWindowMode.SERVER_RECENT_DEFAULT
                        or "default_recent_window" in canonical_gateway_facets
                    )
                )
            )
            and has_grounded_gateway_facet
        )
    else:
        family_valid = False
    if primary_intent is None or not family_valid:
        _LOGGER.info(
            "conversation_preflight_operational_shape_rejected",
            extra={
                "family": proposal.operational_family.value,
                "target_kinds": ",".join(target_kinds),
                "facets": ",".join(sorted(facets)),
            },
        )
        return _reject_operational_promotion("invalid_family_shape")
    return SemanticJudgmentProposal(
        primary_intent=primary_intent,
        targets=tuple(normalized_targets),
        requested_facets=normalized_operational_facets,
        confidence=proposal.confidence,
        ambiguous=False,
        action_posture="advise_only",
        action_subject="none",
        authority="candidate_only",
        execution_authority=False,
    )


def preflight_selects_general_knowledge(
    result: ConversationPreflightResult | None,
    *,
    utterance: str,
    locale: str,
) -> bool:
    """Accept only one confident context-independent general-knowledge route."""
    if result is None:
        return False
    proposal = result.proposal
    return bool(
        result.attempted
        and result.failure_kind is None
        and proposal is not None
        and proposal.social_act is SocialAct.NONE
        and proposal.knowledge_signal is GeneralKnowledgeSignal.EXPLICIT
        and proposal.operational_signal is OperationalSignal.NONE
        and proposal.context_dependency is ContextDependency.NONE
        and proposal.confidence >= _ROUTE_PROMOTION_CONFIDENCE
        and result.input_digest == _preflight_input_digest(utterance)
        and result.proposal_digest == content_digest(proposal.model_dump(mode="json"))
        and result.model_config_digest is not None
        and result.prompt_digest is not None
        and proposal.general_answer is not None
        and proposal.general_answer.locale == ("ko" if locale.casefold().startswith("ko") else "en")
        and proposal.general_answer.profile_digest == result.direct_response_profile_digest
    )


def _preflight_input_digest(utterance: str) -> str:
    return content_digest({"utterance": utterance})


def operational_target_is_generic(value: str) -> bool:
    """Return whether source text names only a generic operational category."""
    normalized = " ".join(value.casefold().split()).strip(".,:;!?()[]{}")
    prefixes = (
        "the ",
        "a ",
        "an ",
        "this ",
        "that ",
        "these ",
        "those ",
        "some ",
        "selected ",
        "current ",
        "our ",
        "my ",
        "your ",
        "their ",
        "its ",
        "해당 ",
        "이 ",
        "그 ",
        "저 ",
        "선택한 ",
        "현재 ",
        "우리 ",
        "내 ",
    )
    while normalized.startswith(prefixes):
        normalized = normalized.removeprefix(
            next(prefix for prefix in prefixes if normalized.startswith(prefix))
        )
    return normalized in _GENERIC_OPERATIONAL_TARGETS or (
        _GENERIC_OPERATIONAL_TARGET_PATTERN.fullmatch(normalized) is not None
    )


def operational_target_is_exact(value: str) -> bool:
    """Return whether a target is an exact token-like name or path identity."""
    return not any(character.isspace() for character in value) and not (
        operational_target_is_generic(value)
    )


def named_subscription_requested(utterance: str) -> bool:
    if _EXPLICIT_NAMED_SUBSCRIPTION.search(utterance) is not None:
        return True
    candidates = (
        *(match.group(1) for match in _SUBSCRIPTION_NAME_AFTER.finditer(utterance)),
        *(match.group(1) for match in _SUBSCRIPTION_NAME_BEFORE_KOREAN.finditer(utterance)),
        *(match.group(1) for match in _SUBSCRIPTION_NAME_BEFORE.finditer(utterance)),
    )
    return any(candidate.casefold() not in _GENERIC_SUBSCRIPTION_WORDS for candidate in candidates)


def operational_time_is_past_hour(value: str) -> bool:
    """Return whether source text explicitly denotes a past one-hour range."""
    return " ".join(value.casefold().split()) in _ONE_HOUR_EXPRESSIONS


def _reject_operational_promotion(reason: str) -> SemanticJudgmentProposal | None:
    _LOGGER.info(
        "conversation_preflight_operational_promotion_rejected",
        extra={"reason": reason},
    )
    return None


def _bounded_context(context: Sequence[str]) -> tuple[str, ...]:
    selected: list[str] = []
    total = 0
    for item in tuple(context)[-_MAX_CONTEXT_ITEMS:]:
        if not isinstance(item, str):
            raise TypeError("conversation preflight context MUST contain strings")
        total += len(item)
        if total > _MAX_CONTEXT_CHARS:
            raise ValueError("conversation preflight context exceeds its bound")
        selected.append(item)
    return tuple(selected)


def _bounded_profile(profile: Mapping[str, Any]) -> dict[str, Any]:
    selected = dict(profile)
    if len(canonical_json(selected).encode()) > _MAX_PROFILE_BYTES:
        raise ValueError("conversation preflight profile exceeds its byte bound")
    return selected


def _repair_instruction(exc: TypeError | ValueError | ValidationError) -> dict[str, str]:
    reason = str(exc)
    if "locale" in reason:
        return {"path": "direct_response.locale", "reason": "copy the supplied locale exactly"}
    if "profile digest" in reason:
        return {
            "path": "direct_response.profile_digest",
            "reason": "copy direct_response_profile_digest exactly",
        }
    if "honorific" in reason:
        return {
            "path": "direct_response.answer",
            "reason": "Korean sentences require polite honorific endings",
        }
    if "links or markup" in reason:
        return {
            "path": "direct_response.answer",
            "reason": "return plain text without links or markup",
        }
    return {
        "path": "proposal",
        "reason": "return every conditionally required field with a schema-valid value",
    }


__all__ = [
    "ContextDependency",
    "ConversationPreflightBinding",
    "ConversationPreflightBoundary",
    "ConversationPreflightModel",
    "ConversationPreflightProposal",
    "ConversationPreflightResult",
    "DIRECT_SOCIAL_ACTS",
    "GeneralKnowledgeDraft",
    "GeneralKnowledgeSignal",
    "OperationalPreflightFamily",
    "OperationalWindowMode",
    "OperationalSignal",
    "SOCIAL_NARRATOR_CAPABILITY_IDS",
    "SocialResponseNarratorBinding",
    "SocialResponseNarratorModel",
    "SocialResponseNarratorResult",
    "SocialAct",
    "named_subscription_requested",
    "operational_target_is_generic",
    "operational_target_is_exact",
    "operational_time_is_past_hour",
    "preflight_selects_general_knowledge",
    "preflight_operational_judgment",
]
