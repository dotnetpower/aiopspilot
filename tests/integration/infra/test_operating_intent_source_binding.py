"""Infrastructure contract for the opt-in six-type operating-intent source binding."""

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[3]
_SERVICE_MAIN = (_ROOT / "infra/services/core-control-plane/main.tf").read_text(encoding="utf-8")
_SERVICE_VARIABLES = (_ROOT / "infra/services/core-control-plane/variables.tf").read_text(
    encoding="utf-8"
)
_MODULE_MAIN = (
    _ROOT / "infra/services/core-control-plane/modules/core-control-plane/main.tf"
).read_text(encoding="utf-8")
_MODULE_VARIABLES = (
    _ROOT / "infra/services/core-control-plane/modules/core-control-plane/variables.tf"
).read_text(encoding="utf-8")


def _assigns(text: str, name: str) -> bool:
    """Return whether ``text`` passes ``var.<name>`` to a ``<name>`` argument.

    ``terraform fmt`` column-aligns every assignment in a block to its widest
    sibling identifier, so exact inter-token spacing shifts whenever a sibling
    variable is added or removed; matching on flexible whitespace keeps this
    check stable across that reformatting.
    """

    return re.search(rf"\b{re.escape(name)}\s*=\s*var\.{re.escape(name)}\b", text) is not None


def test_operating_intent_source_is_explicitly_opt_in() -> None:
    assert 'variable "operating_intent_source"' in _SERVICE_VARIABLES
    assert 'variable "operating_intent_source"' in _MODULE_VARIABLES
    assert _assigns(_SERVICE_MAIN, "operating_intent_source")
    assert "!var.operating_intent_source.enabled ? [] : [" in _MODULE_MAIN


def test_operating_intent_source_threads_exact_revision_digest_and_path() -> None:
    for key in (
        "FDAI_OPERATING_INTENT_SOURCE_PATH",
        "FDAI_OPERATING_INTENT_SOURCE_REVISION",
        "FDAI_OPERATING_INTENT_SOURCE_SHA256",
        "FDAI_OPERATING_INTENT_SOURCE_EXPECTED_COUNTS_JSON",
    ):
        assert key in _MODULE_MAIN

    assert "sha256:[0-9a-f]{64}" in _MODULE_VARIABLES
    assert "exact pinned revision" in _MODULE_VARIABLES
