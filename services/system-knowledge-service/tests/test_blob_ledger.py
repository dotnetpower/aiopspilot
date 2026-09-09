from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

from azure.core.exceptions import (
    ResourceExistsError,
    ResourceModifiedError,
    ResourceNotFoundError,
)
from fdai_system_knowledge_service.blob_ledger import AzureBlobMessageLedger

KEY = "sha256:" + ("a" * 64)


@dataclass
class _Stored:
    body: bytes
    etag: int


class _Download:
    def __init__(self, stored: _Stored) -> None:
        self._stored = stored
        self.properties = SimpleNamespace(etag=str(stored.etag))

    async def readall(self) -> bytes:
        return self._stored.body


class _Blob:
    def __init__(self, container: _Container, name: str) -> None:
        self._container = container
        self._name = name

    async def upload_blob(self, data: bytes, **kwargs: Any) -> None:
        current = self._container.records.get(self._name)
        if current is not None and kwargs.get("overwrite") is False:
            raise ResourceExistsError("exists")
        etag = kwargs.get("etag")
        if current is not None and etag is not None and str(current.etag) != etag:
            raise ResourceModifiedError("changed")
        self._container.records[self._name] = _Stored(
            body=data,
            etag=1 if current is None else current.etag + 1,
        )

    async def download_blob(self) -> _Download:
        try:
            return _Download(self._container.records[self._name])
        except KeyError as exc:
            raise ResourceNotFoundError("missing") from exc

    async def delete_blob(self, **kwargs: Any) -> None:
        try:
            current = self._container.records[self._name]
        except KeyError as exc:
            raise ResourceNotFoundError("missing") from exc
        if str(current.etag) != kwargs.get("etag"):
            raise ResourceModifiedError("changed")
        del self._container.records[self._name]


class _Container:
    def __init__(self) -> None:
        self.records: dict[str, _Stored] = {}
        self.probed = False
        self.closed = False

    async def _properties(self) -> object:
        self.probed = True
        return {}

    def get_container_properties(self, **_kwargs: Any) -> Any:
        return self._properties()

    async def _items(self, prefix: str) -> AsyncIterator[SimpleNamespace]:
        for name in sorted(self.records):
            if name.startswith(prefix):
                yield SimpleNamespace(name=name)

    def list_blobs(
        self,
        name_starts_with: str | None = None,
        include: Any = None,
        **_kwargs: Any,
    ) -> AsyncIterator[SimpleNamespace]:
        del include
        return self._items(name_starts_with or "")

    def get_blob_client(
        self,
        blob: str,
        snapshot: str | None = None,
        *,
        version_id: str | None = None,
    ) -> _Blob:
        del snapshot, version_id
        return _Blob(self, blob)

    async def _close(self) -> None:
        self.closed = True

    def close(self) -> Any:
        return self._close()


class _Credential:
    def __init__(self) -> None:
        self.closed = False

    async def close(self) -> None:
        self.closed = True


def _ledger(
    container: _Container,
    credential: _Credential | None = None,
) -> AzureBlobMessageLedger:
    return AzureBlobMessageLedger(
        container=container,
        credential=credential or _Credential(),
        clock=lambda: datetime(2026, 9, 10, tzinfo=UTC),
    )


async def test_blob_ledger_claims_and_delivers_exactly_once() -> None:
    container = _Container()
    credential = _Credential()
    ledger = _ledger(container, credential)
    await ledger.start()

    assert await ledger.claim(KEY) is True
    assert await ledger.claim(KEY) is False
    await ledger.mark_sending(KEY, "sha256:" + ("b" * 64))
    await ledger.mark_delivered(KEY, "provider-message")

    assert await ledger.state(KEY) == "delivered"
    await ledger.aclose()
    assert container.probed is True
    assert container.closed is True
    assert credential.closed is True


async def test_blob_ledger_reconciles_processing_and_sending_after_restart() -> None:
    container = _Container()
    ledger = _ledger(container)
    await ledger.start()
    assert await ledger.claim(KEY) is True
    await ledger.mark_sending(KEY, "sha256:" + ("b" * 64))

    other_key = "sha256:" + ("c" * 64)
    assert await ledger.claim(other_key) is True

    restarted = _ledger(container)
    await restarted.start()

    assert await restarted.state(KEY) == "ambiguous"
    assert await restarted.state(other_key) is None
    assert await restarted.claim(KEY) is False
    assert await restarted.claim(other_key) is True
