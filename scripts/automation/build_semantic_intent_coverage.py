#!/usr/bin/env python3
"""Build the complete FDAI semantic-intent topic and metric inventory."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from fdai.agents._framework.pantheon import PANTHEON_SPECS
from scripts.automation.semantic_intent_metrics import (
    COVERAGE_LIMITATIONS,
    METRIC_GROUPS,
    OPERATING_DOMAINS,
    SCORING_POLICY,
)


def build_inventory(root: Path) -> dict[str, Any]:
    """Build a source-derived topic inventory and current evaluation coverage."""
    golden = _json(root / "eval/golden-dataset/expectations.json")
    question_bank = _json(root / "eval/golden-dataset/question-bank/question-bank.json")
    question_bank_source = _yaml(
        root / "eval/golden-dataset/question-bank/question-bank.source.yaml"
    )
    intent_cases = _yaml(root / "eval/golden-dataset/azure-incident-intent-golden.yaml")
    function_root = root / "services/core-control-plane/src/fdai/core/ontology_platform"
    function_source_paths = sorted(function_root.glob("*.py"))
    function_names = _query_function_names(function_source_paths)
    golden_functions = Counter(
        function_name
        for case in golden["cases"]
        for function_name in case["semantic_retrieval"]["required_function_types"]
    )
    intent_functions = Counter(
        intent
        for case in intent_cases["cases"]
        for intent in (
            case["expected"]["primary_intent"],
            *case["expected"].get("secondary_intents", []),
        )
        if intent.startswith("query.")
    )
    unknown_function_refs = (set(golden_functions) | set(intent_functions)) - set(function_names)
    if unknown_function_refs:
        raise ValueError(
            "semantic intent sources reference undeclared query functions: "
            f"{sorted(unknown_function_refs)}"
        )
    question_domain_rows = []
    for spec in PANTHEON_SPECS:
        for domain in spec.question_domains:
            question_domain_rows.append(
                {
                    "topic_id": domain,
                    "agent": spec.name,
                    "semantic_contract_case_count": 0,
                    "coverage_state": "unmapped",
                }
            )
    bank_questions = question_bank["questions"]
    bank_domains = Counter(item["domain"] for item in bank_questions)
    bank_categories = Counter(item.get("category") or "uncategorized" for item in bank_questions)
    golden_categories = Counter(item["category"] for item in golden["cases"])
    required_bank_domains = _required_question_bank_domains(question_bank_source)
    required_golden_categories = set(question_bank_source["golden_category_domains"])
    function_rows = [
        {
            "topic_id": name,
            "golden_expectation_count": golden_functions[name],
            "intent_contract_case_count": intent_functions[name],
            "coverage_state": (
                "reviewed_golden"
                if golden_functions[name]
                else ("intent_contract_only" if intent_functions[name] else "missing_case")
            ),
        }
        for name in function_names
    ]
    readiness = Counter(
        (
            item["readiness"]["content_review"],
            item["readiness"]["semantic_contract"],
            item["readiness"]["runtime_binding"],
            item["readiness"]["evidence_source"],
            item["readiness"]["validation"],
        )
        for item in bank_questions
    )
    inventory = {
        "operating_domains": _operating_domain_rows(bank_questions, OPERATING_DOMAINS),
        "question_bank_domains": [
            _question_topic_row(name, bank_domains[name], bank_questions, "domain")
            for name in sorted(required_bank_domains | set(bank_domains))
        ],
        "question_bank_categories": [
            _question_topic_row(name, count, bank_questions, "category")
            for name, count in sorted(bank_categories.items())
        ],
        "golden_categories": [
            {"topic_id": name, "expectation_count": golden_categories[name]}
            for name in sorted(required_golden_categories | set(golden_categories))
        ],
        "pantheon_question_domains": sorted(
            question_domain_rows,
            key=lambda item: (item["agent"], item["topic_id"]),
        ),
        "ontology_query_functions": function_rows,
    }
    reviewed_bank_count = sum(count for keys, count in readiness.items() if keys[0] == "reviewed")
    validated_bank_count = sum(
        count for keys, count in readiness.items() if keys[-1] == "contract_passed"
    )
    pantheon_covered = sum(item["coverage_state"] == "covered" for item in question_domain_rows)
    function_any_covered = sum(item["coverage_state"] != "missing_case" for item in function_rows)
    body = {
        "schema_version": "1.0.0",
        "source_digests": {
            path.relative_to(root).as_posix(): _sha256(path)
            for path in (
                root / "eval/golden-dataset/expectations.json",
                root / "eval/golden-dataset/question-bank/question-bank.json",
                root / "eval/golden-dataset/question-bank/question-bank.source.yaml",
                root / "eval/golden-dataset/azure-incident-intent-golden.yaml",
                root / "services/core-control-plane/src/fdai/agents/_framework/pantheon.py",
                root / "scripts/automation/semantic_intent_metrics.py",
            )
        }
        | {
            "services/core-control-plane/src/fdai/core/ontology_platform/*.py": (
                _paths_digest(root, function_source_paths)
            )
        },
        "topic_inventory": inventory,
        "evaluation_axes": _evaluation_axes(bank_questions, intent_cases["cases"]),
        "scoring_policy": SCORING_POLICY,
        "metric_contract": {group: list(metrics) for group, metrics in METRIC_GROUPS.items()},
        "coverage_metrics": {
            "golden_category_coverage": _ratio(
                len(required_golden_categories & set(golden_categories)),
                len(required_golden_categories),
            ),
            "question_bank_domain_inventory_coverage": _ratio(
                len(required_bank_domains & set(bank_domains)),
                len(required_bank_domains),
            ),
            "question_bank_reviewed_rate": _ratio(reviewed_bank_count, len(bank_questions)),
            "question_bank_contract_validation_rate": _ratio(
                validated_bank_count, len(bank_questions)
            ),
            "pantheon_domain_semantic_contract_coverage": _ratio(
                pantheon_covered, len(question_domain_rows)
            ),
            "ontology_query_function_golden_coverage": _ratio(
                sum(bool(golden_functions[name]) for name in function_names),
                len(function_names),
            ),
            "ontology_query_function_any_contract_coverage": _ratio(
                function_any_covered, len(function_names)
            ),
        },
        "hard_zero_metrics": [
            "candidate_authority_violation_count",
            "execution_authority_violation_count",
            "forbidden_action_false_positive_rate",
            "invented_capability_count",
            "invented_target_identity_count",
            "legacy_ordinary_language_route_count",
            "non_direct_action_false_positive_rate",
            "read_to_action_false_positive_rate",
            "schema_failure_success_fallback_count",
            "executable_action_draft_count",
            "unverified_operational_success_claim_rate",
        ],
        "coverage_limitations": list(COVERAGE_LIMITATIONS),
    }
    body["inventory_digest"] = _digest(body)
    return body


def _question_topic_row(
    name: str,
    count: int,
    questions: list[dict[str, Any]],
    field: str,
) -> dict[str, Any]:
    matching = [item for item in questions if (item.get(field) or "uncategorized") == name]
    reviewed = sum(item["readiness"]["content_review"] == "reviewed" for item in matching)
    contract_validated = sum(
        item["readiness"]["validation"] == "contract_passed" for item in matching
    )
    return {
        "topic_id": name,
        "question_count": count,
        "reviewed": _ratio(reviewed, count),
        "contract_validated": _ratio(contract_validated, count),
    }


def _required_question_bank_domains(source: dict[str, Any]) -> set[str]:
    return (
        set(source["golden_category_domains"].values())
        | {item["domain"] for item in source["manual_domain_ranges"]}
        | {item["domain"] for item in source["console_questions"]}
        | {item["domain"] for item in source["candidate_groups"]}
    )


def _operating_domain_rows(
    questions: list[dict[str, Any]],
    operating_domains: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    rows = []
    for domain, bank_domain_ids in operating_domains.items():
        matching = [item for item in questions if item["domain"] in bank_domain_ids]
        reviewed = sum(item["readiness"]["content_review"] == "reviewed" for item in matching)
        validated = sum(item["readiness"]["validation"] == "contract_passed" for item in matching)
        rows.append(
            {
                "topic_id": domain,
                "mapping_kind": "reviewed_evaluation_crosswalk",
                "question_bank_domains": list(bank_domain_ids),
                "question_count": len(matching),
                "reviewed": _ratio(reviewed, len(matching)),
                "contract_validated": _ratio(validated, len(matching)),
            }
        )
    return rows


def _evaluation_axes(
    questions: list[dict[str, Any]],
    intent_cases: list[dict[str, Any]],
) -> dict[str, list[str]]:
    return {
        "action_postures": sorted(
            {item["safety"]["action_posture"] for item in questions}
            | {item["expected"]["action_posture"] for item in intent_cases}
        ),
        "discourse_modes": sorted({item["expected"]["discourse_mode"] for item in intent_cases}),
        "evidence_postures": [
            "conflicting",
            "fresh",
            "incomplete",
            "stale",
            "unavailable",
        ],
        "locales": ["en", "ko", "mixed"],
        "result_shapes": sorted({item.get("result_shape") or "unspecified" for item in questions}),
        "target_kinds": sorted(
            {target for item in questions for target in item.get("target_kinds", [])}
            | {target["kind"] for item in intent_cases for target in item["expected"]["targets"]}
        ),
        "temporal_scopes": sorted(
            {item.get("temporal_scope") or "unspecified" for item in questions}
        ),
        "terminal_postures": [
            "action_draft",
            "answered",
            "clarification",
            "held",
            "unsupported",
        ],
    }


def _query_function_names(paths: list[Path]) -> list[str]:
    names: set[str] = set()
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Assign, ast.AnnAssign)):
                continue
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            value = node.value
            if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
                continue
            if not value.value.startswith("query."):
                continue
            if any(
                isinstance(target, ast.Name) and target.id.endswith("_FUNCTION_NAME")
                for target in targets
            ):
                names.add(value.value)
    return sorted(names)


def _json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} MUST contain an object")
    return value


def _yaml(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} MUST contain an object")
    return value


def _ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "covered": numerator,
        "total": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def _sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def _paths_digest(root: Path, paths: list[Path]) -> str:
    values = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": _sha256(path),
        }
        for path in paths
    ]
    return _digest({"files": values})


def _digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("eval/golden-dataset/semantic-intent-coverage.json"),
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output if args.output.is_absolute() else root / args.output
    payload = build_inventory(root)
    _write_text(
        output,
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    metrics = payload["coverage_metrics"]
    print(
        "semantic-intent-coverage: "
        + ", ".join(
            f"{name}={value['covered']}/{value['total']}" for name, value in metrics.items()
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
