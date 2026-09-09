from __future__ import annotations

from datetime import datetime

from fdai_system_knowledge_service.application import create_app
from fdai_system_knowledge_service.runtime import KnowledgeTurnResult
from httpx import ASGITransport, AsyncClient


class _Runtime:
    def __init__(self) -> None:
        self.ready = False
        self.closed = False
        self.bodies: list[bytes] = []

    async def start(self) -> None:
        self.ready = True

    async def aclose(self) -> None:
        self.ready = False
        self.closed = True

    async def handle(
        self,
        *,
        body: bytes,
        authorization: str,
        received_at: datetime,
    ) -> KnowledgeTurnResult:
        assert authorization == "Bearer service-token"
        assert received_at.tzinfo is not None
        self.bodies.append(body)
        return KnowledgeTurnResult(state="delivered")


async def test_app_exposes_only_health_and_teams_message_routes() -> None:
    runtime = _Runtime()
    app = create_app(runtime=runtime)

    async with app.router.lifespan_context(app):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            live = await client.get("/health/live")
            ready = await client.get("/health/ready")
            delivered = await client.post(
                "/api/teams/messages",
                content=b"{}",
                headers={
                    "content-type": "application/json",
                    "authorization": "Bearer service-token",
                },
            )
            missing = await client.get("/v1/query")

    assert live.status_code == ready.status_code == 200
    assert delivered.status_code == 202
    assert delivered.json() == {"status": "delivered"}
    assert runtime.bodies == [b"{}"]
    assert missing.status_code == 404
    assert runtime.closed is True


async def test_app_rejects_non_json_and_oversized_body_before_runtime() -> None:
    runtime = _Runtime()
    app = create_app(runtime=runtime)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        media = await client.post("/api/teams/messages", content=b"{}")
        large = await client.post(
            "/api/teams/messages",
            content=b"x" * 256_001,
            headers={"content-type": "application/json"},
        )

    assert media.status_code == 415
    assert large.status_code == 413
    assert runtime.bodies == []
