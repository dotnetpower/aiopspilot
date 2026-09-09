#!/usr/bin/env python3
"""Export non-secret WARA scope settings from one exact deployed job."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

_COMMAND = ("python", "-m", "fdai.delivery.wara_assessment_cli")
_ALLOWED_ENV = (
    "FDAI_WARA_INVENTORY_FRESHNESS_SECONDS",
    "FDAI_WARA_MAX_RESOURCES",
    "FDAI_WARA_WORKLOAD_IDS_JSON",
)


def extract_wara_context(raw: object) -> dict[str, str]:
    """Return bounded non-secret settings from exactly one WARA job definition."""

    if not isinstance(raw, list):
        raise ValueError("Container Apps jobs payload MUST be a JSON array")
    matches: list[dict[str, Any]] = []
    for job in raw:
        if not isinstance(job, dict):
            raise ValueError("Container Apps job entries MUST be objects")
        properties = job.get("properties")
        template = properties.get("template") if isinstance(properties, dict) else None
        containers = template.get("containers") if isinstance(template, dict) else None
        if not isinstance(containers, list):
            continue
        for container in containers:
            if not isinstance(container, dict):
                continue
            command = container.get("command")
            if command == list(_COMMAND):
                matches.append(container)
    if len(matches) != 1:
        raise ValueError("exactly one deployed WARA assessment container is required")
    env = matches[0].get("env")
    if not isinstance(env, list):
        raise ValueError("deployed WARA assessment environment is missing")
    values = {
        str(item.get("name")): str(item.get("value"))
        for item in env
        if isinstance(item, dict)
        and isinstance(item.get("name"), str)
        and isinstance(item.get("value"), str)
    }
    workload_ids = values.get("FDAI_WARA_WORKLOAD_IDS_JSON", "")
    try:
        parsed: object = json.loads(workload_ids)
    except json.JSONDecodeError as error:
        raise ValueError("deployed WARA workload ids are invalid JSON") from error
    if (
        not isinstance(parsed, list)
        or len(parsed) != 1
        or not isinstance(parsed[0], str)
        or not parsed[0].strip()
    ):
        raise ValueError("deployed WARA job MUST bind exactly one workload id")
    selected = {
        name: values[name] for name in _ALLOWED_ENV if name in values and values[name].strip()
    }
    if "FDAI_WARA_WORKLOAD_IDS_JSON" not in selected:
        raise ValueError("deployed WARA workload ids are missing")
    if any("\n" in value or "\r" in value for value in selected.values()):
        raise ValueError("deployed WARA settings cannot contain line breaks")
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--github-env", type=Path, required=True)
    args = parser.parse_args()
    raw = json.loads(args.jobs.read_text(encoding="utf-8"))
    values = extract_wara_context(raw)
    with args.github_env.open("a", encoding="utf-8") as stream:
        for name in sorted(values):
            stream.write(f"{name}={values[name]}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
