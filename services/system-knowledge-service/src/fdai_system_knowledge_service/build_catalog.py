"""Command-line compiler for the packaged system-knowledge catalog."""

from __future__ import annotations

import argparse
from pathlib import Path

from fdai_system_knowledge_service.catalog import compile_reference_catalog, write_catalog


def main() -> int:
    """Compile the reviewed catalog and write one runtime artifact."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    catalog = compile_reference_catalog(arguments.repo_root)
    write_catalog(catalog, arguments.output)
    print(
        f"system-knowledge-catalog: records={len(catalog.records)} digest={catalog.catalog_digest}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
