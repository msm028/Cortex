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


def run_action(action: dict[str, Any], policy_result: dict[str, str] | None) -> dict[str, Any]:
    action_cwd = REPO_ROOT / action["cwd"]
    cmd = action["cmd"]
    completed = subprocess.run(cmd, cwd=action_cwd, capture_output=True, text=True, check=False)
    return {
        "id": action["id"],
        "type": action["type"],
        "cwd": action["cwd"],
        "cmd": cmd,
        "destructive": action["destructive"],
        "policy_decision": policy_result,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "started_at": None,
        "finished_at": None,
    }


def write_audit_log(
    plan_path: Path,
    status: str,
    action_results: list[dict[str, Any]],
    policy_results: list[dict[str, str]],
    approval_metadata: dict[str, str] | None,
) -> Path:
    AUDIT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    audit_path = AUDIT_DIR / f"{plan_path.name}.{timestamp}.audit.json"
    payload = {
        "plan": str(plan_path.relative_to(REPO_ROOT)),
        "status": status,
        "executed_at": now_utc(),
        "approval": approval_metadata,
        "policy_results": policy_results,
        "action_results": action_results,
    }
    audit_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return audit_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Execute a validated plan file")
    parser.add_argument("--plan", required=True, help="Path to plan JSON file")
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
        print(f"[RUN] {action['id']}: {' '.join(action['cmd'])} (cwd={action['cwd']})")
        result = run_action(action, policy_by_action.get(action["id"]))
        result["started_at"] = started_at
        result["finished_at"] = now_utc()
        action_results.append(result)

        if result["stdout"]:
            print(result["stdout"], end="" if result["stdout"].endswith("\n") else "\n")
        if result["stderr"]:
            print(result["stderr"], end="" if result["stderr"].endswith("\n") else "\n")

        if result["exit_code"] != 0:
            audit_path = write_audit_log(plan_path, "failed", action_results, policy_results, approval_metadata)
            print(f"[FAIL] Action failed: {action['id']} (exit={result['exit_code']})")
            print(f"[INFO] Audit log: {audit_path.relative_to(REPO_ROOT)}")
            return 1

    audit_path = write_audit_log(plan_path, "passed", action_results, policy_results, approval_metadata)
    print(f"[PASS] Plan executed successfully: {plan_path.relative_to(REPO_ROOT)}")
    print(f"[INFO] Audit log: {audit_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
