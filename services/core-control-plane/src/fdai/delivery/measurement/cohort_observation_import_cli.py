"""CLI composition for protected cohort observation imports."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from fdai.core.measurement.cohort_claim_policy import load_cohort_claim_policy
from fdai.delivery.measurement.cohort_observation_import import (
    CohortObservationImportContext,
    import_cohort_observation_batch,
    load_cohort_observation_batch,
)
from fdai.delivery.persistence import PostgresStateStore, PostgresStateStoreConfig
from fdai_service_contracts.baseline_cohort import CohortArm


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--arm", choices=[item.value for item in CohortArm], required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--source-workflow-path", required=True)
    parser.add_argument("--source-run-id", type=int, required=True)
    parser.add_argument("--source-run-attempt", type=int, required=True)
    parser.add_argument("--source-artifact-name", required=True)
    parser.add_argument("--imported-at")
    return parser


async def _run(args: argparse.Namespace) -> dict[str, object]:
    dsn = os.environ.get("FDAI_STATE_STORE_DSN", "").strip()
    if not dsn:
        raise ValueError("FDAI_STATE_STORE_DSN MUST be configured")
    imported_at = (
        datetime.now(tz=UTC)
        if args.imported_at is None
        else datetime.fromisoformat(str(args.imported_at).replace("Z", "+00:00"))
    )
    policy = load_cohort_claim_policy(args.policy)
    report = await import_cohort_observation_batch(
        load_cohort_observation_batch(args.batch),
        context=CohortObservationImportContext(
            arm=CohortArm(args.arm),
            fdai_revision=args.revision,
            source_workflow_path=args.source_workflow_path,
            source_run_id=args.source_run_id,
            source_run_attempt=args.source_run_attempt,
            source_artifact_name=args.source_artifact_name,
            imported_at=imported_at,
        ),
        policy=policy,
        store=PostgresStateStore(config=PostgresStateStoreConfig(dsn=dsn)),
    )
    return report.to_mapping()


def main(argv: list[str] | None = None) -> int:
    """Import one protected batch and print only its aggregate result."""

    args = _parser().parse_args(argv)
    result = asyncio.run(_run(args))
    print(json.dumps(result, separators=(",", ":"), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
