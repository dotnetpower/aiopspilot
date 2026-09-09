"""Ed25519 license verifier and issuer-key custody tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)
from fdai.delivery.trust import (
    Ed25519LicenseVerifier,
    license_public_key_pem,
    private_key_matches_public_key,
)


def _key_pair() -> tuple[Ed25519PrivateKey, bytes, bytes]:
    private_key = Ed25519PrivateKey.generate()
    private_pem = private_key.private_bytes(
        Encoding.PEM,
        PrivateFormat.PKCS8,
        NoEncryption(),
    )
    public_pem = private_key.public_key().public_bytes(
        Encoding.PEM,
        PublicFormat.SubjectPublicKeyInfo,
    )
    return private_key, private_pem, public_pem


def test_verifier_accepts_only_the_matching_signature() -> None:
    signer, _private_pem, public_pem = _key_pair()
    other, _other_private_pem, _other_public_pem = _key_pair()
    document = b"canonical-license-document"
    verifier = Ed25519LicenseVerifier(public_pem)

    assert verifier.verify(document, signer.sign(document)) is True
    assert verifier.verify(document, other.sign(document)) is False


def test_private_key_match_requires_the_matching_owner_only_key(tmp_path: Path) -> None:
    _signer, private_pem, public_pem = _key_pair()
    _other, _other_private_pem, other_public_pem = _key_pair()
    private_path = tmp_path / "license-signing-key.pem"
    private_path.write_bytes(private_pem)
    private_path.chmod(0o600)

    assert private_key_matches_public_key(private_path, public_pem) is True
    assert private_key_matches_public_key(private_path, other_public_pem) is False

    private_path.chmod(0o644)
    with pytest.raises(PermissionError, match="mode 0600"):
        private_key_matches_public_key(private_path, public_pem)


def test_packaged_public_key_is_a_valid_ed25519_key() -> None:
    verifier = Ed25519LicenseVerifier(license_public_key_pem())

    assert verifier.verify(b"not-signed", b"x" * 64) is False
