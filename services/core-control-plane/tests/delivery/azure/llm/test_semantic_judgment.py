"""Strict structured-output contracts for semantic judgment."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fdai.core.conversation.conversation_preflight import ConversationPreflightProposal
from fdai.delivery.azure.llm.request_target import ModelRequestTarget
from fdai.delivery.azure.llm.semantic_judgment import (
    AzureOpenAISemanticJudgmentModel,
    AzureOpenAISemanticJudgmentModelConfig,
    _strict_response_format,
)
from fdai.shared.providers.workload_identity import IdentityToken
from fdai_service_contracts.semantic_judgment import SemanticJudgmentProposal


def _assert_strict_objects(value: object) -> None:
    if isinstance(value, Mapping):
        properties = value.get("properties")
        if isinstance(properties, Mapping):
            assert value.get("additionalProperties") is False
            assert value.get("required") == list(properties)
        assert not {
            "default",
            "title",
            "minLength",
            "maxLength",
            "minItems",
            "maxItems",
        }.intersection(value)
        for nested in value.values():
            _assert_strict_objects(nested)
    elif isinstance(value, list):
        for nested in value:
            _assert_strict_objects(nested)


def test_semantic_judgment_uses_strict_structured_output() -> None:
    response_format = _strict_response_format(
        SemanticJudgmentProposal.model_json_schema(),
        name="semantic-judgment",
    )

    assert response_format["type"] == "json_schema"
    envelope = response_format["json_schema"]
    assert isinstance(envelope, Mapping)
    assert envelope["name"] == "semantic-judgment"
    assert envelope["strict"] is True
    _assert_strict_objects(envelope["schema"])


def test_conversation_preflight_uses_the_same_strict_contract() -> None:
    response_format = _strict_response_format(
        ConversationPreflightProposal.model_json_schema(),
        name="conversation-preflight",
    )

    envelope = response_format["json_schema"]
    assert isinstance(envelope, Mapping)
    _assert_strict_objects(envelope["schema"])


def test_strict_structured_output_normalizes_schema_name_without_regex() -> None:
    response_format = _strict_response_format(
        SemanticJudgmentProposal.model_json_schema(),
        name="semantic judgment/v1",
    )

    envelope = response_format["json_schema"]
    assert isinstance(envelope, Mapping)
    assert envelope["name"] == "semantic_judgment_v1"


@pytest.mark.asyncio
async def test_conversation_preflight_never_fails_over_to_a_second_candidate() -> None:
    requests: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(503, request=request)

    class _Identity:
        async def get_token(self, audience: str) -> IdentityToken:
            return IdentityToken(
                "test-token",
                datetime.now(UTC) + timedelta(minutes=5),
                audience,
            )

    candidates = tuple(
        ModelRequestTarget(
            endpoint=f"https://candidate-{index}.example",
            deployment=f"candidate-{index}",
            api_version="2024-06-01",
        )
        for index in (1, 2)
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = AzureOpenAISemanticJudgmentModel(
            identity=_Identity(),
            http_client=client,
            config=AzureOpenAISemanticJudgmentModelConfig(
                candidates=candidates,
                system_prompt="Judge.",
                preflight_system_prompt="Classify.",
            ),
            owner_loop=asyncio.get_running_loop(),
        )
        result = await asyncio.to_thread(
            model.preflight,
            utterance="Compare blue-green and canary.",
            context=(),
            locale="en",
            direct_response_profile={"identity": "Bragi"},
            direct_response_profile_digest="sha256:" + ("a" * 64),
            schema_repair=(),
        )

    assert result is None
    assert len(requests) == 1
    assert "candidate-1" in str(requests[0].url)


@pytest.mark.asyncio
async def test_gpt5_conversation_preflight_uses_low_reasoning_effort() -> None:
    requests: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        requests.append(json.loads(request.content))
        return httpx.Response(503, request=request)

    class _Identity:
        async def get_token(self, audience: str) -> IdentityToken:
            return IdentityToken(
                "test-token",
                datetime.now(UTC) + timedelta(minutes=5),
                audience,
            )

    candidate = ModelRequestTarget(
        endpoint="https://candidate.example",
        deployment="gpt-5.6-sol",
        api_version="2024-12-01-preview",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = AzureOpenAISemanticJudgmentModel(
            identity=_Identity(),
            http_client=client,
            config=AzureOpenAISemanticJudgmentModelConfig(
                candidates=(candidate,),
                system_prompt="Judge.",
                preflight_system_prompt="Classify.",
            ),
            owner_loop=asyncio.get_running_loop(),
        )
        result = await asyncio.to_thread(
            model.preflight,
            utterance="Compare blue-green and canary.",
            context=(),
            locale="en",
            direct_response_profile={"identity": "Bragi"},
            direct_response_profile_digest="sha256:" + ("a" * 64),
            schema_repair=(),
        )

    assert result is None
    assert requests[0]["reasoning_effort"] == "low"


@pytest.mark.asyncio
async def test_conversation_preflight_cancellation_stops_the_provider_request() -> None:
    started = asyncio.Event()
    provider_cancelled = asyncio.Event()
    cancelled = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            provider_cancelled.set()
            raise
        return httpx.Response(200, request=request)

    class _Identity:
        async def get_token(self, audience: str) -> IdentityToken:
            return IdentityToken(
                "test-token",
                datetime.now(UTC) + timedelta(minutes=5),
                audience,
            )

    candidate = ModelRequestTarget(
        endpoint="https://candidate.example",
        deployment="candidate",
        api_version="2024-06-01",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = AzureOpenAISemanticJudgmentModel(
            identity=_Identity(),
            http_client=client,
            config=AzureOpenAISemanticJudgmentModelConfig(
                candidates=(candidate,),
                system_prompt="Judge.",
                preflight_system_prompt="Classify.",
            ),
            owner_loop=asyncio.get_running_loop(),
        )
        pending = asyncio.create_task(
            asyncio.to_thread(
                model.preflight,
                utterance="Compare blue-green and canary.",
                context=(),
                locale="en",
                direct_response_profile={"identity": "Bragi"},
                direct_response_profile_digest="sha256:" + ("a" * 64),
                schema_repair=(),
                cancelled=cancelled,
            )
        )
        await asyncio.wait_for(started.wait(), timeout=1)
        cancelled.set()
        assert await asyncio.wait_for(pending, timeout=1) is None
        await asyncio.wait_for(provider_cancelled.wait(), timeout=1)


@pytest.mark.asyncio
async def test_parent_cancellation_stops_the_provider_request() -> None:
    started = asyncio.Event()
    provider_cancelled = asyncio.Event()

    async def handler(request: httpx.Request) -> httpx.Response:
        started.set()
        try:
            await asyncio.sleep(60)
        except asyncio.CancelledError:
            provider_cancelled.set()
            raise
        return httpx.Response(200, request=request)

    class _Identity:
        async def get_token(self, audience: str) -> IdentityToken:
            return IdentityToken(
                "test-token",
                datetime.now(UTC) + timedelta(minutes=5),
                audience,
            )

    candidate = ModelRequestTarget(
        endpoint="https://candidate.example",
        deployment="candidate",
        api_version="2024-06-01",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = AzureOpenAISemanticJudgmentModel(
            identity=_Identity(),
            http_client=client,
            config=AzureOpenAISemanticJudgmentModelConfig(
                candidates=(candidate,),
                system_prompt="Judge.",
                preflight_system_prompt="Classify.",
            ),
            owner_loop=asyncio.get_running_loop(),
        )
        pending = asyncio.create_task(
            model._complete(
                "{}",
                input_digest="sha256:" + ("a" * 64),
                proposal_schema=ConversationPreflightProposal.model_json_schema(),
                system_prompt="Classify.",
                call_kind="conversation-preflight",
                max_tokens=512,
                temperature=0.0,
                timeout_seconds=10,
                allow_candidate_failover=False,
            )
        )
        await asyncio.wait_for(started.wait(), timeout=1)
        pending.cancel()
        with pytest.raises(asyncio.CancelledError):
            await pending
        await asyncio.wait_for(provider_cancelled.wait(), timeout=1)
