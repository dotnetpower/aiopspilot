"""ASGI application for the independent System Knowledge Service."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator, Mapping
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Protocol

import httpx
from azure.identity.aio import ClientSecretCredential, ManagedIdentityCredential
from fdai_service_contracts.venue import ExecutionVenue
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from fdai_system_knowledge_service.catalog import load_catalog
from fdai_system_knowledge_service.config import SystemKnowledgeSettings
from fdai_system_knowledge_service.ledger import MessageLedger
from fdai_system_knowledge_service.runtime import SystemKnowledgeRuntime
from fdai_system_knowledge_service.search import SystemKnowledgeIndex
from fdai_system_knowledge_service.teams import (
    AzureChannelTokenProvider,
    PyJwtServiceTokenVerifier,
    RemoteJwksProvider,
    TeamsIngressError,
    TeamsMentionVerifier,
    TeamsPublisher,
    TeamsPublishError,
)

_MAX_BODY_BYTES = 256_000


class KnowledgeHttpRuntime(Protocol):
    """Route-safe lifecycle and activity surface."""

    @property
    def ready(self) -> bool: ...

    async def start(self) -> None: ...

    async def aclose(self) -> None: ...

    async def handle(
        self,
        *,
        body: bytes,
        authorization: str,
        received_at: datetime,
    ) -> object: ...


class _ComposedRuntime:
    """Close the knowledge runtime and its service-owned HTTP client together."""

    def __init__(
        self,
        *,
        runtime: SystemKnowledgeRuntime,
        http_client: httpx.AsyncClient,
    ) -> None:
        self._runtime = runtime
        self._http_client = http_client

    @property
    def ready(self) -> bool:
        return self._runtime.ready

    async def start(self) -> None:
        try:
            await self._runtime.start()
        except BaseException:
            await self.aclose()
            raise

    async def aclose(self) -> None:
        try:
            await self._runtime.aclose()
        finally:
            await self._http_client.aclose()

    async def handle(
        self,
        *,
        body: bytes,
        authorization: str,
        received_at: datetime,
    ) -> object:
        return await self._runtime.handle(
            body=body,
            authorization=authorization,
            received_at=received_at,
        )


def create_runtime(settings: SystemKnowledgeSettings) -> KnowledgeHttpRuntime:
    """Compose service-owned catalog, Teams trust, durable claims, and publisher."""

    catalog = load_catalog(
        settings.catalog_path,
        expected_source_revision=settings.expected_source_revision,
    )
    http_client = httpx.AsyncClient(
        trust_env=False,
        limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
    )
    jwks = RemoteJwksProvider(url=settings.teams.jwks_url, http_client=http_client)
    credential = (
        ClientSecretCredential(
            tenant_id=settings.teams.tenant_id,
            client_id=settings.teams.application_id,
            client_secret=settings.teams.client_secret or "",
        )
        if settings.execution_venue is ExecutionVenue.LOCAL
        else ManagedIdentityCredential(client_id=settings.managed_identity_client_id)
    )
    token_provider = AzureChannelTokenProvider(credential)
    publisher = TeamsPublisher(http_client=http_client, tokens=token_provider)
    runtime = SystemKnowledgeRuntime(
        ingress=TeamsMentionVerifier(
            settings=settings.teams,
            tokens=PyJwtServiceTokenVerifier(
                application_id=settings.teams.application_id,
                jwks=jwks,
            ),
        ),
        index=SystemKnowledgeIndex(catalog),
        ledger=MessageLedger(settings.ledger_path),
        publisher=publisher,
    )
    return _ComposedRuntime(runtime=runtime, http_client=http_client)


def create_app(
    environ: Mapping[str, str] | None = None,
    *,
    runtime: KnowledgeHttpRuntime | None = None,
) -> Starlette:
    """Build the standalone health and Teams activity application."""

    selected = runtime or create_runtime(
        SystemKnowledgeSettings.parse(os.environ if environ is None else environ)
    )

    @asynccontextmanager
    async def lifespan(_app: Starlette) -> AsyncIterator[None]:
        await selected.start()
        try:
            yield
        finally:
            await selected.aclose()

    async def live(_request: Request) -> Response:
        return JSONResponse({"status": "ok"})

    async def ready(_request: Request) -> Response:
        return JSONResponse(
            {"status": "ok" if selected.ready else "unavailable"},
            status_code=200 if selected.ready else 503,
        )

    async def teams(request: Request) -> Response:
        if request.headers.get("content-type", "").split(";", 1)[0] != "application/json":
            return JSONResponse({"error": {"code": "unsupported_media_type"}}, status_code=415)
        body = await _bounded_request_body(request)
        if body is None:
            return JSONResponse({"error": {"code": "body_too_large"}}, status_code=413)
        authorization = request.headers.get("authorization", "")
        try:
            result = await selected.handle(
                body=body,
                authorization=authorization,
                received_at=datetime.now(UTC),
            )
        except TeamsIngressError as exc:
            return JSONResponse({"error": {"code": exc.code}}, status_code=exc.http_status)
        except TeamsPublishError as exc:
            return JSONResponse({"error": {"code": exc.code}}, status_code=503)
        state = getattr(result, "state", "accepted")
        return JSONResponse({"status": state}, status_code=202)

    return Starlette(
        routes=[
            Route("/health/live", live, methods=["GET"]),
            Route("/health/ready", ready, methods=["GET"]),
            Route("/api/teams/messages", teams, methods=["POST"]),
        ],
        lifespan=lifespan,
    )


async def _bounded_request_body(request: Request) -> bytes | None:
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > _MAX_BODY_BYTES:
            return None
    return bytes(body)


__all__ = ["KnowledgeHttpRuntime", "create_app", "create_runtime"]
