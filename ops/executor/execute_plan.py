#!/usr/bin/env python3
"""Execute validated plans and write deterministic audit logs."""

from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = REPO_ROOT / "artifacts" / "audit"


def parse_bool_arg(value: str) -> bool:
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise argparse.ArgumentTypeError(f"Invalid boolean value: {value}")


def load_validate_module():
    module_path = REPO_ROOT / "ops" / "plan" / "validate_plan.py"
    spec = importlib.util.spec_from_file_location("validate_plan_module", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load validator module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def action_command(action: dict[str, Any]) -> list[str]:
    action_type = action["type"]
    if action_type == "shell":
        return list(action["cmd"])
    if action_type == "docker_compose":
        return ["docker", "compose", *list(action["args"])]
    if action_type == "terraform":
        return ["terraform", *list(action["args"])]
    raise ValueError(f"Unsupported action type: {action_type}")


def action_cwd(action: dict[str, Any]) -> Path:
    action_type = action["type"]
    if action_type == "shell":
        return REPO_ROOT / action["cwd"]
    if action_type == "docker_compose":
        return REPO_ROOT / action["project_dir"]
    if action_type == "terraform":
        return REPO_ROOT / action["workdir"]
    raise ValueError(f"Unsupported action type: {action_type}")


def run_action(
    action: dict[str, Any],
    policy_result: dict[str, str] | None,
    dry_run: bool,
    allow_infra_exec: bool,
) -> dict[str, Any]:
    cmd = action_command(action)
    cwd_path = action_cwd(action)

    result: dict[str, Any] = {
        "id": action["id"],
        "type": action["type"],
        "destructive": action["destructive"],
        "policy_decision": policy_result,
        "cmd": cmd,
        "cwd": str(cwd_path.relative_to(REPO_ROOT)),
        "dry_run": dry_run,
        "stdout": "",
        "stderr": "",
        "exit_code": 0,
        "started_at": None,
        "finished_at": None,
    }

    if dry_run:
        result["stdout"] = f"DRY RUN: would execute {' '.join(cmd)} in {result['cwd']}\n"
        return result

    if action["type"] in {"docker_compose", "terraform"} and not allow_infra_exec:
        result["exit_code"] = 1
        result["stderr"] = "Infra execution refused: set --allow-infra-exec true to run infra actions.\n"
        return result

    completed = subprocess.run(cmd, cwd=cwd_path, capture_output=True, text=True, check=False)
    result["exit_code"] = completed.returncode
    result["stdout"] = completed.stdout
    result["stderr"] = completed.stderr

    if action["type"] == "shell":
        stripped = completed.stdout.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                payload = json.loads(stripped)
            except json.JSONDecodeError:
                payload = None
            if isinstance(payload, dict):
                for key, value in payload.items():
                    if isinstance(value, (str, int, float, bool)) or value is None:
                        result[key] = value
    return result


def write_audit_log(
    plan_path: Path,
    status: str,
    action_results: list[dict[str, Any]],
    policy_results: list[dict[str, str]],
    approval_metadata: dict[str, Any] | None,
    dry_run: bool,
    allow_infra_exec: bool,
) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_path = AUDIT_DIR / f"{plan_path.name}.{timestamp}.audit.json"
    payload = {
        "plan": str(plan_path.relative_to(REPO_ROOT)),
        "status": status,
        "executed_at": now_utc(),
        "dry_run": dry_run,
        "allow_infra_exec": allow_infra_exec,
        "approval": approval_metadata,
        "policy_results": policy_results,
        "action_results": action_results,
    }
    audit_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a validated plan file")
    parser.add_argument("--plan", required=True, help="Path to plan JSON file")
    parser.add_argument(
        "--dry-run",
        nargs="?",
        const="true",
        default="true",
        type=parse_bool_arg,
        help="Run without executing commands. Bare flag implies true (default: true).",
    )
    parser.add_argument(
        "--allow-infra-exec",
        nargs="?",
        const="true",
        default="false",
        type=parse_bool_arg,
        help="Allow infra execution when dry-run is false. Bare flag implies true (default: false).",
    )
    args = parser.parse_args()

    validator = load_validate_module()
    ok, plan, plan_path, errors, policy_results, approval_metadata = validator.validate_plan_file(args.plan)
    for result in policy_results:
        print(
            f"[POLICY] action_id={result['action_id']} decision={result['decision']} reason={result['reason']}"
        )
    if not ok or plan is None:
        print(f"[FAIL] Plan validation failed: {plan_path}")
        for error in errors:
            print(f"  - {error}")
        return 1

    print(f"[PASS] Plan validated: {plan_path.relative_to(REPO_ROOT)}")

    actions = plan.get("actions", [])
    action_results: list[dict[str, Any]] = []
    policy_by_action = {entry["action_id"]: entry for entry in policy_results}

    for action in actions:
        started_at = now_utc()
        cmd = " ".join(action_command(action))
        print(f"[RUN] {action['id']}: {cmd}")
        result = run_action(action, policy_by_action.get(action["id"]), args.dry_run, args.allow_infra_exec)
        result["started_at"] = started_at
        result["finished_at"] = now_utc()
        action_results.append(result)

        if result["stdout"]:
            print(result["stdout"], end="" if result["stdout"].endswith("\n") else "\n")
        if result["stderr"]:
            print(result["stderr"], end="" if result["stderr"].endswith("\n") else "\n")

        if result["exit_code"] != 0:
            audit_path = write_audit_log(
                plan_path,
                "failed",
                action_results,
                policy_results,
                approval_metadata,
                args.dry_run,
                args.allow_infra_exec,
            )
            print(f"[FAIL] Action failed: {action['id']} (exit={result['exit_code']})")
            print(f"[INFO] Audit log: {audit_path.relative_to(REPO_ROOT)}")
            return 1

    audit_path = write_audit_log(
        plan_path,
        "passed",
        action_results,
        policy_results,
        approval_metadata,
        args.dry_run,
        args.allow_infra_exec,
    )
    print(f"[PASS] Plan executed successfully: {plan_path.relative_to(REPO_ROOT)}")
    print(f"[INFO] Audit log: {audit_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
