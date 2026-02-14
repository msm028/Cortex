#!/usr/bin/env python3
"""Validate deterministic plan files and approval gates."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TOP_LEVEL_SCHEMA = {
    "version": int,
    "created_at": str,
    "env": str,
    "target": str,
    "actions": list,
}


def canonical_json_bytes(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def normalize_plan_path(plan_arg: str) -> Path:
    path = Path(plan_arg)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def validate_cwd(cwd: str) -> bool:
    path = Path(cwd)
    if path.is_absolute():
        return False
    if any(part == ".." for part in path.parts):
        return False
    return True


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def validate_plan_data(plan: object, errors: list[str]) -> None:
    require(isinstance(plan, dict), "Plan root must be a JSON object.", errors)
    if not isinstance(plan, dict):
        return

    for key, expected_type in TOP_LEVEL_SCHEMA.items():
        require(key in plan, f"Missing top-level key: {key}", errors)
        if key in plan:
            require(
                isinstance(plan[key], expected_type),
                f"Top-level key {key} must be of type {expected_type.__name__}.",
                errors,
            )

    actions = plan.get("actions")
    if not isinstance(actions, list):
        return

    for idx, action in enumerate(actions):
        label = f"actions[{idx}]"
        require(isinstance(action, dict), f"{label} must be an object.", errors)
        if not isinstance(action, dict):
            continue

        for key, expected_type in (("id", str), ("type", str), ("cwd", str), ("cmd", list), ("destructive", bool)):
            require(key in action, f"{label} missing key: {key}", errors)
            if key in action:
                require(
                    isinstance(action[key], expected_type),
                    f"{label}.{key} must be of type {expected_type.__name__}.",
                    errors,
                )

        action_type = action.get("type")
        if isinstance(action_type, str):
            require(action_type == "shell", f"{label}.type must be 'shell'.", errors)

        action_cwd = action.get("cwd")
        if isinstance(action_cwd, str):
            require(validate_cwd(action_cwd), f"{label}.cwd must be relative and must not contain '..'.", errors)

        action_cmd = action.get("cmd")
        if isinstance(action_cmd, list):
            require(len(action_cmd) > 0, f"{label}.cmd must not be empty.", errors)
            if len(action_cmd) > 0:
                require(
                    all(isinstance(part, str) for part in action_cmd),
                    f"{label}.cmd must contain only strings.",
                    errors,
                )


def parse_expected_digest(sha_path: Path) -> str:
    first_line = sha_path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not first_line:
        return ""
    token = first_line[0].strip().split()[0] if first_line[0].strip() else ""
    return token


def validate_plan_file(plan_arg: str) -> tuple[bool, dict | None, Path, list[str]]:
    errors: list[str] = []
    plan_path = normalize_plan_path(plan_arg)
    plan_data: dict | None = None

    require(plan_path.is_file(), f"Plan file not found: {plan_path}", errors)
    if errors:
        return False, None, plan_path, errors

    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Plan file is not valid JSON: {exc}")
        return False, None, plan_path, errors

    validate_plan_data(loaded, errors)

    canonical = canonical_json_bytes(loaded)
    computed_digest = hashlib.sha256(canonical).hexdigest()
    sha_path = Path(str(plan_path) + ".sha256")

    require(sha_path.is_file(), f"Hash file not found: {sha_path}", errors)
    if sha_path.is_file():
        expected_digest = parse_expected_digest(sha_path)
        require(bool(re.fullmatch(r"[0-9a-f]{64}", expected_digest)), f"Invalid SHA256 format in {sha_path}", errors)
        if re.fullmatch(r"[0-9a-f]{64}", expected_digest):
            require(
                expected_digest == computed_digest,
                f"Hash mismatch for {plan_path.name}: expected {expected_digest}, computed {computed_digest}",
                errors,
            )

    actions = loaded.get("actions", []) if isinstance(loaded, dict) else []
    has_destructive = any(isinstance(action, dict) and action.get("destructive") is True for action in actions)
    if has_destructive:
        approval_path = Path(str(plan_path) + ".approved")
        require(approval_path.is_file(), f"Destructive plan requires approval file: {approval_path}", errors)
        if approval_path.is_file():
            approval_text = approval_path.read_text(encoding="utf-8", errors="replace")
            require(
                re.search(r"(?m)^vaultwarden_item_id:\s*\S+\s*$", approval_text) is not None,
                f"Approval file must contain 'vaultwarden_item_id: <...>': {approval_path}",
                errors,
            )

    if isinstance(loaded, dict):
        plan_data = loaded

    return len(errors) == 0, plan_data, plan_path, errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a deterministic plan file")
    parser.add_argument("--plan", required=True, help="Path to plan JSON file")
    args = parser.parse_args()

    ok, _plan, plan_path, errors = validate_plan_file(args.plan)
    if ok:
        print(f"[PASS] Plan validation succeeded: {plan_path.relative_to(REPO_ROOT)}")
        return 0

    print(f"[FAIL] Plan validation failed: {plan_path}")
    for error in errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
