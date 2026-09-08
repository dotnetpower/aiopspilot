"""Exact target, time, and subscription-scope checks for typed preflight."""

from __future__ import annotations

import re

GENERIC_SUBSCRIPTION_SCOPE_FILTERS = frozenset(
    {"subscription", "the subscription", "current subscription", "구독", "현재 구독"}
)
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
_TARGET_PREFIXES = (
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


def operational_target_is_generic(value: str) -> bool:
    """Return whether source text names only a generic operational category."""

    normalized = " ".join(value.casefold().split()).strip(".,:;!?()[]{}")
    while normalized.startswith(_TARGET_PREFIXES):
        normalized = normalized.removeprefix(
            next(prefix for prefix in _TARGET_PREFIXES if normalized.startswith(prefix))
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
    """Return whether the utterance asks for a non-generic subscription."""

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


__all__ = [
    "GENERIC_SUBSCRIPTION_SCOPE_FILTERS",
    "named_subscription_requested",
    "operational_target_is_exact",
    "operational_target_is_generic",
    "operational_time_is_past_hour",
]
