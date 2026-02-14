#!/usr/bin/env python3
"""Validate deterministic plan files, policy gates, and approval rules."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = REPO_ROOT / "policies" / "command-policy.json"
TOP_LEVEL_SCHEMA = {
    "version": int,
    "created_at": str,
    "env": str,
    "target": str,
    "actions": list,
}
REQUIRED_APPROVAL_KEYS = ("vaultwarden_item_id", "plan_sha256")


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


def parse_key_value_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip()
    return values


def load_policy(errors: list[str]) -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        errors.append(f"Policy file not found: {POLICY_PATH}")
        return {}

    try:
        policy = json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Policy file is not valid JSON: {exc}")
        return {}

    require(isinstance(policy, dict), "Policy root must be a JSON object.", errors)
    if not isinstance(policy, dict):
        return {}

    for key, expected_type in ("version", int), ("deny", list), ("require_approval", list), ("allow_by_env", dict):
        require(key in policy, f"Policy missing key: {key}", errors)
        if key in policy:
            require(
                isinstance(policy[key], expected_type),
                f"Policy key {key} must be {expected_type.__name__}.",
                errors,
            )

    if isinstance(policy.get("deny"), list):
        require(all(isinstance(item, str) for item in policy["deny"]), "Policy deny entries must be strings.", errors)
    if isinstance(policy.get("require_approval"), list):
        require(
            all(isinstance(item, str) for item in policy["require_approval"]),
            "Policy require_approval entries must be strings.",
            errors,
        )

    allow_by_env = policy.get("allow_by_env")
    if isinstance(allow_by_env, dict):
        for env_name, patterns in allow_by_env.items():
            require(isinstance(env_name, str), "Policy allow_by_env keys must be strings.", errors)
            require(isinstance(patterns, list), f"Policy allow_by_env.{env_name} must be a list.", errors)
            if isinstance(patterns, list):
                require(
                    all(isinstance(item, str) for item in patterns),
                    f"Policy allow_by_env.{env_name} entries must be strings.",
                    errors,
                )

    return policy


def pattern_matches(pattern: str, cmd_tokens: list[str], cmd_text: str) -> bool:
    if pattern.startswith("re:"):
        return re.search(pattern[len("re:") :], cmd_text) is not None
    return pattern in cmd_text or pattern in cmd_tokens


def allow_pattern_matches(pattern: str, cmd_tokens: list[str], cmd_text: str) -> bool:
    if pattern.endswith("/"):
        return cmd_text.startswith(pattern)
    if " " not in pattern:
        return bool(cmd_tokens) and cmd_tokens[0] == pattern
    return cmd_text.startswith(pattern)


def evaluate_action_policy(action: dict[str, Any], plan_env: str, policy: dict[str, Any]) -> tuple[str, str]:
    cmd_tokens = action.get("cmd", [])
    cmd_text = " ".join(cmd_tokens)

    for pattern in policy.get("deny", []):
        if pattern_matches(pattern, cmd_tokens, cmd_text):
            return "DENY", f"matched deny pattern '{pattern}'"

    allow_patterns = policy.get("allow_by_env", {}).get(plan_env)
    if not isinstance(allow_patterns, list):
        return "DENY", f"no allowlist configured for env '{plan_env}'"

    if not any(allow_pattern_matches(pattern, cmd_tokens, cmd_text) for pattern in allow_patterns):
        return "DENY", f"command not allowed in env '{plan_env}'"

    if action.get("destructive") is True:
        return "REQUIRE_APPROVAL", "action marked destructive=true"

    for pattern in policy.get("require_approval", []):
        if pattern_matches(pattern, cmd_tokens, cmd_text):
            return "REQUIRE_APPROVAL", f"matched approval pattern '{pattern}'"

    return "ALLOW", f"allowed in env '{plan_env}'"


def validate_plan_file(
    plan_arg: str,
) -> tuple[bool, dict[str, Any] | None, Path, list[str], list[dict[str, str]], dict[str, str] | None]:
    errors: list[str] = []
    policy_results: list[dict[str, str]] = []
    approval_metadata: dict[str, str] | None = None
    plan_path = normalize_plan_path(plan_arg)
    plan_data: dict[str, Any] | None = None

    require(plan_path.is_file(), f"Plan file not found: {plan_path}", errors)
    if errors:
        return False, None, plan_path, errors, policy_results, approval_metadata

    try:
        loaded = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Plan file is not valid JSON: {exc}")
        return False, None, plan_path, errors, policy_results, approval_metadata

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

    policy = load_policy(errors)

    actions = loaded.get("actions", []) if isinstance(loaded, dict) else []
    plan_env = loaded.get("env") if isinstance(loaded, dict) and isinstance(loaded.get("env"), str) else ""

    needs_approval = False
    for idx, action in enumerate(actions):
        if not isinstance(action, dict):
            continue
        action_id = action.get("id", f"actions[{idx}]")
        if not isinstance(action_id, str):
            action_id = f"actions[{idx}]"

        if action.get("destructive") is True:
            needs_approval = True

        if not policy:
            decision = "DENY"
            reason = "policy unavailable"
        else:
            decision, reason = evaluate_action_policy(action, plan_env, policy)

        policy_results.append({"action_id": action_id, "decision": decision, "reason": reason})

        if decision == "DENY":
            errors.append(f"Action {action_id} denied by policy: {reason}")
        if decision == "REQUIRE_APPROVAL":
            needs_approval = True

    if needs_approval:
        approval_path = Path(str(plan_path) + ".approved")
        require(approval_path.is_file(), f"Plan requires approval file: {approval_path}", errors)
        if approval_path.is_file():
            approval_values = parse_key_value_file(approval_path)
            for key in REQUIRED_APPROVAL_KEYS:
                require(key in approval_values and bool(approval_values[key]), f"Approval missing key '{key}': {approval_path}", errors)

            plan_sha256 = approval_values.get("plan_sha256", "")
            if plan_sha256:
                require(
                    bool(re.fullmatch(r"[0-9a-f]{64}", plan_sha256)),
                    f"Approval key 'plan_sha256' is not a valid sha256: {approval_path}",
                    errors,
                )
                if re.fullmatch(r"[0-9a-f]{64}", plan_sha256):
                    require(
                        plan_sha256 == computed_digest,
                        "Approval plan_sha256 mismatch: expected computed plan hash "
                        f"{computed_digest} but found {plan_sha256}",
                        errors,
                    )

            if "vaultwarden_item_id" in approval_values and "plan_sha256" in approval_values and not errors:
                approval_metadata = {
                    "vaultwarden_item_id": approval_values["vaultwarden_item_id"],
                    "plan_sha256": approval_values["plan_sha256"],
                }
                if approval_values.get("approved_at"):
                    approval_metadata["approved_at"] = approval_values["approved_at"]

    if isinstance(loaded, dict):
        plan_data = loaded

    return len(errors) == 0, plan_data, plan_path, errors, policy_results, approval_metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a deterministic plan file")
    parser.add_argument("--plan", required=True, help="Path to plan JSON file")
    args = parser.parse_args()

    ok, _plan, plan_path, errors, policy_results, approval_metadata = validate_plan_file(args.plan)
    for result in policy_results:
        print(
            f"[POLICY] action_id={result['action_id']} decision={result['decision']} reason={result['reason']}"
        )

    if ok:
        if approval_metadata is not None:
            print(
                "[APPROVAL] "
                f"vaultwarden_item_id={approval_metadata.get('vaultwarden_item_id')} "
                f"plan_sha256={approval_metadata.get('plan_sha256')} "
                f"approved_at={approval_metadata.get('approved_at', '')}"
            )
        print(f"[PASS] Plan validation succeeded: {plan_path.relative_to(REPO_ROOT)}")
        return 0

    print(f"[FAIL] Plan validation failed: {plan_path}")
    for error in errors:
        print(f"  - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
