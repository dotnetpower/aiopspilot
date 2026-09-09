from __future__ import annotations

import hashlib
import os
from pathlib import Path

import pytest
from test_oci_archive import make_archive

from fdai_deployment_cli.contracts import canonical_bytes
from fdai_deployment_cli.runtime_build import build_runtime_release
from fdai_deployment_cli.runtime_release import (
    RUNTIME_SERVICES,
    load_runtime_release,
    validate_runtime_images,
)

COMMIT = "a" * 40
PLATFORM = "linux-x86_64"


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path, dict[str, object]]:
    source = tmp_path / "artifacts"
    source.mkdir(mode=0o700)

    def image(name: str, *, dependency: bool = False) -> dict[str, str]:
        base = source / "images" / name
        base.mkdir(parents=True)
        archive = base / "image.oci.tar"
        fixture = make_archive(archive, config_updates={"config": {}} if dependency else None)
        sbom = base / "sbom.cdx.json"
        provenance = base / "provenance.jsonl"
        sbom.write_text('{"bomFormat":"CycloneDX","specVersion":"1.5"}\n', encoding="utf-8")
        provenance.write_text('{"verificationMaterial":"synthetic-test-only"}\n', encoding="utf-8")
        return {
            "archive": archive.relative_to(source).as_posix(),
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "sbom": sbom.relative_to(source).as_posix(),
            "sbom_sha256": hashlib.sha256(sbom.read_bytes()).hexdigest(),
            "provenance": provenance.relative_to(source).as_posix(),
            "provenance_sha256": hashlib.sha256(provenance.read_bytes()).hexdigest(),
            "image_digest": fixture.manifest_digest,
        }

    def opaque(name: str) -> dict[str, str]:
        base = source / name
        base.mkdir(parents=True)
        archive = base / "payload.tar.gz"
        sbom = base / "sbom.cdx.json"
        archive.write_bytes(f"synthetic {name} archive".encode())
        sbom.write_text('{"bomFormat":"CycloneDX","specVersion":"1.5"}\n', encoding="utf-8")
        return {
            "archive": archive.relative_to(source).as_posix(),
            "archive_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
            "sbom": sbom.relative_to(source).as_posix(),
            "sbom_sha256": hashlib.sha256(sbom.read_bytes()).hexdigest(),
        }

    descriptor: dict[str, object] = {
        "schema_version": "fdai.runtime-release-build.v1",
        "source_commit": COMMIT,
        "platform_tag": PLATFORM,
        "services": {name: image(name) for name in sorted(RUNTIME_SERVICES)},
        "sidecars": {"clamav": image("clamav", dependency=True)},
        "console": opaque("console"),
        "deployment_support": opaque("deployment-support"),
    }
    descriptor_path = tmp_path / "runtime-build.json"
    descriptor_path.write_bytes(canonical_bytes(descriptor))
    descriptor_path.chmod(0o600)
    bundle = tmp_path / "deployment-bundle.tar.gz"
    bundle.write_bytes(b"synthetic signed deployment bundle")
    return source, descriptor_path, bundle, descriptor


def _build(tmp_path: Path) -> tuple[dict[str, object], Path, dict[str, object]]:
    source, descriptor, bundle, raw = _fixture(tmp_path)
    output = tmp_path / "release"
    return build_runtime_release(source, descriptor, bundle, output), output, raw


def test_builds_complete_v2_release_from_prebuilt_local_artifacts(tmp_path: Path) -> None:
    result, output, descriptor = _build(tmp_path)

    release = load_runtime_release(
        output,
        expected_source_commit=COMMIT,
        expected_platform_tag=PLATFORM,
    )
    images = validate_runtime_images(output, release)
    catalog = release.to_mapping()
    assert result == {
        "schema_version": "fdai.runtime-release-build-result.v1",
        "runtime_release_digest": release.digest,
        "deployment_bundle_sha256": hashlib.sha256(
            b"synthetic signed deployment bundle"
        ).hexdigest(),
        "source_commit": COMMIT,
        "platform_tag": PLATFORM,
        "artifact_count": 22,
        "image_content_digests": images,
        "azure_mutation_performed": False,
        "production_release_eligibility": "unverified",
    }
    assert catalog["schema_version"] == "fdai.runtime-release.v2"
    assert set(catalog["services"]) == RUNTIME_SERVICES
    assert set(catalog["sidecars"]) == {"clamav"}
    assert set(images) == {
        *(f"services/{name}" for name in RUNTIME_SERVICES),
        "sidecars/clamav",
    }
    for section in ("services", "sidecars"):
        for record in catalog[section].values():
            assert str(record["archive"]).endswith("/image.oci.tar")
            assert str(record["sbom"]).endswith("/sbom.cdx.json")
            assert str(record["provenance"]).endswith("/provenance.jsonl")
    assert not (output / "runtime/.fdai-incomplete").exists()
    assert descriptor["services"] != catalog["services"]


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ("schema", "schema_version"),
        ("extra-field", "fields"),
        ("missing-service", "services"),
        ("extra-sidecar", "sidecars"),
        ("bad-commit", "source_commit"),
        ("bad-platform", "platform_tag"),
        ("bad-digest", "image digest"),
        ("traversal", "source path"),
    ],
)
def test_rejects_descriptor_that_cannot_define_one_closed_release(
    tmp_path: Path, change: str, message: str
) -> None:
    source, descriptor_path, bundle, descriptor = _fixture(tmp_path)
    if change == "schema":
        descriptor["schema_version"] = "fdai.runtime-release-build.v2"
    elif change == "extra-field":
        descriptor["extra"] = True
    elif change == "missing-service":
        descriptor["services"].pop("operator-service")
    elif change == "extra-sidecar":
        descriptor["sidecars"]["opa"] = descriptor["sidecars"]["clamav"]
    elif change == "bad-commit":
        descriptor["source_commit"] = "a" * 39
    elif change == "bad-platform":
        descriptor["platform_tag"] = "windows-x86_64"
    elif change == "bad-digest":
        descriptor["services"]["operator-service"]["image_digest"] = "sha256:" + "A" * 64
    else:
        descriptor["console"]["archive"] = "../console.tar.gz"
    descriptor_path.write_bytes(canonical_bytes(descriptor))
    descriptor_path.chmod(0o600)

    with pytest.raises(ValueError, match=message):
        build_runtime_release(source, descriptor_path, bundle, tmp_path / "release")

    assert not (tmp_path / "release").exists()


@pytest.mark.parametrize("failure", ["missing", "empty", "symlink", "fifo", "changed-image"])
def test_rejects_invalid_payload_before_publishing_release(tmp_path: Path, failure: str) -> None:
    source, descriptor_path, bundle, descriptor = _fixture(tmp_path)
    record = descriptor["services"]["core-control-plane"]
    path = source / record["archive"]
    if failure == "missing":
        path.unlink()
    elif failure == "empty":
        path.write_bytes(b"")
    elif failure == "symlink":
        path.unlink()
        path.symlink_to(source / descriptor["services"]["operator-service"]["archive"])
    elif failure == "fifo":
        path.unlink()
        os.mkfifo(path)
    else:
        path.write_bytes(b"not an OCI archive")

    with pytest.raises(ValueError):
        build_runtime_release(source, descriptor_path, bundle, tmp_path / "release")

    assert not (tmp_path / "release").exists()


def test_rejects_duplicate_descriptor_keys(tmp_path: Path) -> None:
    source, descriptor_path, bundle, _descriptor = _fixture(tmp_path)
    payload = descriptor_path.read_bytes().replace(
        b'"schema_version":',
        b'"schema_version":"duplicate","schema_version":',
        1,
    )
    descriptor_path.write_bytes(payload)
    descriptor_path.chmod(0o600)

    with pytest.raises(ValueError, match="duplicate"):
        build_runtime_release(source, descriptor_path, bundle, tmp_path / "release")


def test_private_descriptor_and_new_output_are_required(tmp_path: Path) -> None:
    source, descriptor, bundle, _raw = _fixture(tmp_path)
    descriptor.chmod(0o644)
    with pytest.raises(PermissionError, match="mode-0600"):
        build_runtime_release(source, descriptor, bundle, tmp_path / "release")

    descriptor.chmod(0o600)
    output = tmp_path / "release"
    output.mkdir(mode=0o700)
    with pytest.raises(ValueError, match="already exists"):
        build_runtime_release(source, descriptor, bundle, output)


def test_marker_removal_failure_leaves_only_an_explicit_incomplete_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source, descriptor, bundle, _raw = _fixture(tmp_path)
    output = tmp_path / "release"
    original = Path.unlink

    def fail_marker(path: Path, *args: object, **kwargs: object) -> None:
        if path.name == ".fdai-incomplete":
            raise PermissionError("synthetic marker failure")
        original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "unlink", fail_marker)
    with pytest.raises(ValueError, match="publication is incomplete"):
        build_runtime_release(source, descriptor, bundle, output)

    assert (output / "runtime/.fdai-incomplete").is_file()
    with pytest.raises(ValueError, match="exact file set"):
        load_runtime_release(
            output,
            expected_source_commit=COMMIT,
            expected_platform_tag=PLATFORM,
        )
    with pytest.raises(ValueError, match="already exists"):
        build_runtime_release(source, descriptor, bundle, output)


def test_wrong_service_revision_and_dependency_revision_are_not_equivalent(
    tmp_path: Path,
) -> None:
    source, descriptor_path, bundle, descriptor = _fixture(tmp_path)
    service = descriptor["services"]["core-control-plane"]
    replacement = make_archive(
        source / service["archive"],
        config_updates={"config": {"Labels": {"org.opencontainers.image.revision": "b" * 40}}},
    )
    service["image_digest"] = replacement.manifest_digest
    service["archive_sha256"] = hashlib.sha256(
        (source / service["archive"]).read_bytes()
    ).hexdigest()
    descriptor_path.write_bytes(canonical_bytes(descriptor))
    descriptor_path.chmod(0o600)

    with pytest.raises(ValueError, match="revision"):
        build_runtime_release(source, descriptor_path, bundle, tmp_path / "release")
