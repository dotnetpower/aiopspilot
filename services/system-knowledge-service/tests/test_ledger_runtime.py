from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from fdai_system_knowledge_service.catalog import load_catalog
from fdai_system_knowledge_service.ledger import MessageLedger
from fdai_system_knowledge_service.runtime import SystemKnowledgeRuntime
from fdai_system_knowledge_service.search import SystemKnowledgeIndex
from fdai_system_knowledge_service.teams import VerifiedKnowledgeTurn

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = (
    REPO_ROOT
    / "services/system-knowledge-service/src/fdai_system_knowledge_service/data/catalog.json"
)


class _Ingress:
    def __init__(self, turn: VerifiedKnowledgeTurn) -> None:
        self.turn = turn
        self.warmed = False

    async def warm(self) -> None:
        self.warmed = True

    async def parse(self, **_kwargs: object) -> VerifiedKnowledgeTurn:
        return self.turn


class _Publisher:
    def __init__(self) -> None:
        self.calls = 0
        self.closed = False
        self.payload: object | None = None

    async def send(self, **kwargs: object) -> str:
        self.calls += 1
        self.payload = kwargs["payload"]
        return "reply-example"

    async def aclose(self) -> None:
        self.closed = True


def _turn() -> VerifiedKnowledgeTurn:
    return VerifiedKnowledgeTurn(
        conversation_id="conversation-example",
        message_id="message-example",
        sender_id="aad-user-example",
        principal_id="knowledge-reader-example",
        principal_scope_digest="sha256:" + ("a" * 64),
        service_url="https://smba.trafficmanager.net/example",
        query="How does FDAI keep actions safe?",
        locale="en",
        verification_ref="teams-service-key:key-example",
    )


async def test_runtime_delivers_once_and_suppresses_duplicate_after_restart(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite3"
    publisher = _Publisher()
    ingress = _Ingress(_turn())
    runtime = SystemKnowledgeRuntime(
        ingress=ingress,  # type: ignore[arg-type]
        index=SystemKnowledgeIndex(load_catalog(CATALOG_PATH)),
        ledger=MessageLedger(ledger_path),
        publisher=publisher,  # type: ignore[arg-type]
    )
    await runtime.start()

    first = await runtime.handle(
        body=b"",
        authorization="Bearer token",
        received_at=datetime.now(UTC),
    )
    duplicate = await runtime.handle(
        body=b"{}",
        authorization="Bearer token",
        received_at=datetime.now(UTC),
    )
    await runtime.aclose()

    restarted = MessageLedger(ledger_path)
    await restarted.start()

    assert ingress.warmed is True
    assert first.state == "delivered"
    assert duplicate.duplicate is True
    assert publisher.calls == 1
    assert publisher.closed is True
    assert await restarted.state(_turn().message_key) == "delivered"


async def test_startup_turns_interrupted_send_into_ambiguous_terminal(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ledger.sqlite3"
    ledger = MessageLedger(ledger_path)
    await ledger.start()
    assert await ledger.claim("message-key") is True
    await ledger.mark_sending("message-key", "sha256:" + ("b" * 64))

    restarted = MessageLedger(ledger_path)
    await restarted.start()

    assert await restarted.state("message-key") == "ambiguous"
    assert await restarted.claim("message-key") is False
