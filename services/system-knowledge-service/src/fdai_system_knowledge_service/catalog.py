"""Compile and load the release-bound system-knowledge catalog."""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from fdai_service_contracts.system_knowledge import (
    SystemKnowledgeCatalog,
    SystemKnowledgeRecord,
    SystemKnowledgeSource,
    system_knowledge_digest,
)

from fdai_system_knowledge_service.seeds import REFERENCE_SEEDS, KnowledgeSeed, SeedSource

_GIT = shutil.which("git")


def compile_reference_catalog(
    repo_root: Path,
    *,
    generated_at: datetime | None = None,
) -> SystemKnowledgeCatalog:
    """Compile reviewed records against the current repository source coordinates."""

    root = repo_root.resolve()
    source_revision = _git_output(root, "rev-parse", "HEAD")
    records = tuple(
        sorted(
            (_compile_seed(root, seed) for seed in REFERENCE_SEEDS),
            key=lambda record: record.knowledge_id,
        )
    )
    body = {
        "schema_version": "1.0.0",
        "source_revision": source_revision,
        "generated_at": generated_at or datetime.now(UTC),
        "records": records,
        "execution_authority": False,
    }
    return SystemKnowledgeCatalog.model_validate(
        {
            **body,
            "catalog_digest": system_knowledge_digest(body),
        }
    )


def load_catalog(
    path: Path,
    *,
    expected_source_revision: str | None = None,
) -> SystemKnowledgeCatalog:
    """Load one exact catalog and optionally fence it to the running release."""

    raw = json.loads(path.read_text(encoding="utf-8"))
    catalog = SystemKnowledgeCatalog.model_validate(raw)
    if expected_source_revision is not None and catalog.source_revision != expected_source_revision:
        raise ValueError("system knowledge catalog source revision does not match the runtime")
    return catalog


def write_catalog(catalog: SystemKnowledgeCatalog, path: Path) -> None:
    """Write canonical UTF-8 JSON for the service runtime image."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            catalog.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _compile_seed(root: Path, seed: KnowledgeSeed) -> SystemKnowledgeRecord:
    sources = tuple(
        sorted(
            (_compile_source(root, source) for source in seed.sources),
            key=lambda source: source.evidence_ref,
        )
    )
    body = {
        "knowledge_id": seed.knowledge_id,
        "subject_id": seed.subject_id,
        "title": seed.title,
        "status": seed.status,
        "owner": seed.owner,
        "question_aliases": seed.question_aliases,
        "designed_behavior": seed.designed_behavior,
        "implemented_behavior": seed.implemented_behavior,
        "limitations": seed.limitations,
        "sources": sources,
        "execution_authority": False,
    }
    return SystemKnowledgeRecord.model_validate(
        {
            **body,
            "record_digest": system_knowledge_digest(body),
        }
    )


def _compile_source(root: Path, source: SeedSource) -> SystemKnowledgeSource:
    path = (root / source.path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("system knowledge source escaped the repository") from exc
    if not path.is_file():
        raise FileNotFoundError(f"system knowledge source is missing: {source.path}")
    if _is_ignored(root, source.path):
        raise ValueError(f"system knowledge source is ignored: {source.path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    line_number = _find_symbol(lines, source.symbol)
    blob_sha = _git_output(root, "hash-object", source.path)
    return SystemKnowledgeSource(
        source_kind=source.source_kind,
        authority_role=source.authority_role,
        path=source.path,
        symbol=source.symbol,
        line_start=line_number,
        line_end=line_number,
        blob_sha=blob_sha,
    )


def _find_symbol(lines: list[str], symbol: str) -> int:
    candidates = (
        f"class {symbol}",
        f"def {symbol}",
        f"async def {symbol}",
        f"# {symbol}",
        f"## {symbol}",
        f"### {symbol}",
        f"{symbol} =",
    )
    for index, line in enumerate(lines, start=1):
        stripped = line.strip()
        if any(stripped.startswith(candidate) for candidate in candidates):
            return index
    for index, line in enumerate(lines, start=1):
        if symbol in line:
            return index
    raise ValueError(f"system knowledge source symbol is missing: {symbol}")


def _is_ignored(root: Path, relative: str) -> bool:
    git = _require_git()
    completed = subprocess.run(  # noqa: S603 - fixed executable and arguments
        [git, "check-ignore", "-q", "--", relative],
        cwd=root,
        check=False,
        capture_output=True,
    )
    return completed.returncode == 0


def _git_output(root: Path, *arguments: str) -> str:
    git = _require_git()
    completed = subprocess.run(  # noqa: S603 - fixed executable with compiler-owned arguments
        [git, *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    value = completed.stdout.strip()
    if len(value) != 40 or any(character not in "0123456789abcdef" for character in value):
        raise ValueError("system knowledge Git identity is invalid")
    return value


def _require_git() -> str:
    if _GIT is None:
        raise RuntimeError("git is required to compile the system knowledge catalog")
    return _GIT


__all__ = ["compile_reference_catalog", "load_catalog", "write_catalog"]
