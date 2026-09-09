"""Read authoritative source axes for the conversation quality scorecard."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any


def digest(value: dict[str, Any]) -> str:
    encoded = json.dumps(value, allow_nan=False, separators=(",", ":"), sort_keys=True)
    return f"sha256:{hashlib.sha256(encoded.encode()).hexdigest()}"


def enum_values(path: Path, class_name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        values = [
            item.value.value
            for item in node.body
            if isinstance(item, ast.Assign)
            and isinstance(item.value, ast.Constant)
            and isinstance(item.value.value, str)
        ]
        if values:
            return sorted(values)
        break
    raise ValueError(f"{path} does not declare string enum {class_name}")


def has_answer_oracle(case: dict[str, Any]) -> bool:
    oracle = case.get("answer_oracle")
    return bool(
        isinstance(oracle, dict)
        and oracle.get("required_fact_kinds")
        and oracle.get("required_limitations")
        and isinstance(oracle.get("forbidden_claims"), list)
        and oracle.get("execution_authority") is False
    )


def json_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} MUST contain an object")
    return value


def paths_digest(root: Path, paths: list[Path]) -> str:
    values = [
        {
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256(path),
        }
        for path in paths
    ]
    return digest({"files": values})


def presentation_registry_kinds(path: Path) -> set[str]:
    values = set(
        re.findall(
            r"^\s+([a-z][a-z0-9_]*): registration\(",
            path.read_text(encoding="utf-8"),
            re.MULTILINE,
        )
    )
    if not values:
        raise ValueError(f"{path} does not declare presentation registrations")
    return values


def query_function_names(paths: list[Path]) -> list[str]:
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


def required_question_bank_domains(source: dict[str, Any]) -> set[str]:
    return (
        set(source["golden_category_domains"].values())
        | {item["domain"] for item in source["manual_domain_ranges"]}
        | {item["domain"] for item in source["console_questions"]}
        | {item["domain"] for item in source["candidate_groups"]}
    )


def ratio(numerator: int, denominator: int) -> dict[str, Any]:
    return {
        "covered": numerator,
        "total": denominator,
        "rate": numerator / denominator if denominator else None,
    }


def sha256(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def string_set_assignment(path: Path, assignment_name: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if (
            not isinstance(node, ast.Assign)
            or not any(
                isinstance(target, ast.Name) and target.id == assignment_name
                for target in node.targets
            )
            or not isinstance(node.value, ast.Call)
            or not node.value.args
            or not isinstance(node.value.args[0], (ast.Set, ast.Tuple, ast.List))
        ):
            continue
        values = [
            item.value
            for item in node.value.args[0].elts
            if isinstance(item, ast.Constant) and isinstance(item.value, str)
        ]
        if len(values) == len(node.value.args[0].elts):
            return sorted(values)
        break
    raise ValueError(f"{path} does not declare string set {assignment_name}")


def typescript_string_union(path: Path, type_name: str) -> list[str]:
    source = path.read_text(encoding="utf-8")
    match = re.search(
        rf"export type {re.escape(type_name)}\s*=\s*(.*?);",
        source,
        re.DOTALL,
    )
    if match is None:
        raise ValueError(f"{path} does not declare string union {type_name}")
    values = sorted(set(re.findall(r'"([^"]+)"', match.group(1))))
    if not values:
        raise ValueError(f"{path} string union {type_name} is empty")
    return values


def yaml_object(path: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} MUST contain an object")
    return value
