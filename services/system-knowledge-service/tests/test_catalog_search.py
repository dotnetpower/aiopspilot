from __future__ import annotations

from pathlib import Path

import pytest
from fdai_service_contracts.system_knowledge import SystemKnowledgeQueryRequest
from fdai_system_knowledge_service.catalog import compile_reference_catalog, load_catalog
from fdai_system_knowledge_service.search import SystemKnowledgeIndex

REPO_ROOT = Path(__file__).resolve().parents[3]
CATALOG_PATH = (
    REPO_ROOT
    / "services/system-knowledge-service/src/fdai_system_knowledge_service/data/catalog.json"
)


def _request(query: str, *, locale: str = "en") -> SystemKnowledgeQueryRequest:
    return SystemKnowledgeQueryRequest(
        query=query,
        locale=locale,
        principal_scope_digest="sha256:" + ("a" * 64),
    )


def test_packaged_catalog_matches_current_reviewed_sources() -> None:
    packaged = load_catalog(CATALOG_PATH)
    rebuilt = compile_reference_catalog(REPO_ROOT, generated_at=packaged.generated_at)

    assert rebuilt.catalog_digest == packaged.catalog_digest
    assert rebuilt.source_revision == packaged.source_revision
    assert len(rebuilt.records) == 14


def test_exact_alias_and_korean_paraphrase_return_grounded_records() -> None:
    index = SystemKnowledgeIndex(load_catalog(CATALOG_PATH))

    exact = index.search(_request("How does FDAI keep actions safe?"))
    korean = index.search(_request("FDAI 시스템 지식 봇은 어떻게 동작하나요?", locale="ko"))

    assert exact.matches[0].match_kind == "exact_alias"
    assert exact.matches[0].record.knowledge_id == "action-safety"
    assert korean.matches[0].record.knowledge_id == "system-knowledge-service"
    assert all(match.record.sources for match in korean.matches)
    assert exact.execution_authority is False


def test_unrelated_query_returns_complete_empty_result() -> None:
    result = SystemKnowledgeIndex(load_catalog(CATALOG_PATH)).search(
        _request("zxqv unrelated-token-4931")
    )

    assert result.outcome == "empty"
    assert result.matches == ()
    assert result.complete is True


def test_catalog_revision_fence_rejects_another_release() -> None:
    with pytest.raises(ValueError, match="source revision"):
        load_catalog(CATALOG_PATH, expected_source_revision="f" * 40)
