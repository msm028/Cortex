#!/usr/bin/env python3
"""Create deterministic plan files with canonical JSON hashing."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLANS_DIR = REPO_ROOT / "plans"


def canonical_json_bytes(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def build_default_plan(created_at: str) -> dict:
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "local-repo",
        "actions": [
            {
                "id": "validate-repo",
                "type": "shell",
                "cwd": ".",
                "cmd": ["make", "validate"],
                "destructive": False,
            }
        ],
    }


def build_approval_demo_plan(created_at: str) -> dict:
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "local-repo",
        "actions": [
            {
                "id": "approval-demo-git-status",
                "type": "shell",
                "cwd": ".",
                "cmd": ["git", "status"],
                "destructive": True,
            }
        ],
    }


def build_infra_demo_plan(created_at: str) -> dict:
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "local-repo",
        "actions": [
            {
                "id": "docker-compose-config-demo",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/demo",
                "args": ["config"],
                "destructive": False,
            },
            {
                "id": "terraform-fmt-check-demo",
                "type": "terraform",
                "workdir": "infra/modules/demo",
                "args": ["fmt", "-check"],
                "destructive": False,
            },
        ],
    }


def build_bootstrap_core_dry_run_plan(created_at: str) -> dict:
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "local-repo",
        "actions": [
            {
                "id": "core-compose-config",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/core",
                "args": ["config"],
                "destructive": False,
            }
        ],
    }


def build_bootstrap_core_up_plan(created_at: str) -> dict:
    health_check_script = (
        "import json,subprocess,sys;"
        "names=['core-postgres-1','core-minio-1','core-vaultwarden-1'];"
        "cmd=['docker','inspect',*names,'--format','{{json .State.Health.Status}}'];"
        "out=subprocess.check_output(cmd,text=True).splitlines();"
        "statuses=[json.loads(line) for line in out if line.strip()];"
        "ok=(len(statuses)==3 and all(status=='healthy' for status in statuses));"
        "print('health_statuses',dict(zip(names,statuses)));"
        "sys.exit(0 if ok else 1)"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "core-up",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/core",
                "args": ["up", "-d"],
                "destructive": False,
            },
            {
                "id": "core-ps",
                "type": "shell",
                "cwd": ".",
                "cmd": ["docker", "ps", "--format", "{{.Names}} {{.Status}}"],
                "destructive": False,
            },
            {
                "id": "core-health",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", health_check_script],
                "destructive": False,
            },
        ],
    }


def build_bootstrap_core_down_plan(created_at: str) -> dict:
    verify_down_script = (
        "import subprocess,sys;"
        "target={'core-postgres-1','core-minio-1','core-vaultwarden-1'};"
        "out=subprocess.check_output(['docker','ps','-a','--format','{{.Names}}'],text=True).splitlines();"
        "present=sorted(name for name in out if name in target);"
        "print('remaining',present);"
        "sys.exit(0 if not present else 1)"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "core-down",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/core",
                "args": ["down"],
                "destructive": False,
            },
            {
                "id": "core-verify-down",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", verify_down_script],
                "destructive": False,
            },
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic execution plan")
    parser.add_argument(
        "--name-prefix",
        default="plan",
        help="Filename prefix for the generated plan (default: plan)",
    )
    parser.add_argument(
        "--template",
        default="default",
        choices=(
            "default",
            "approval-demo",
            "infra-demo",
            "bootstrap-core-dry-run",
            "bootstrap-core-up",
            "bootstrap-core-down",
        ),
        help="Plan template (default: default)",
    )
    args = parser.parse_args()

    timestamp = dt.datetime.now(dt.timezone.utc)
    ts_compact = timestamp.strftime("%Y%m%dT%H%M%SZ")
    created_at = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

    if args.template == "approval-demo":
        plan = build_approval_demo_plan(created_at)
    elif args.template == "infra-demo":
        plan = build_infra_demo_plan(created_at)
    elif args.template == "bootstrap-core-dry-run":
        plan = build_bootstrap_core_dry_run_plan(created_at)
    elif args.template == "bootstrap-core-up":
        plan = build_bootstrap_core_up_plan(created_at)
    elif args.template == "bootstrap-core-down":
        plan = build_bootstrap_core_down_plan(created_at)
    else:
        plan = build_default_plan(created_at)
    canonical = canonical_json_bytes(plan)
    digest = hashlib.sha256(canonical).hexdigest()

    PLANS_DIR.mkdir(parents=True, exist_ok=True)
    plan_path = PLANS_DIR / f"{args.name_prefix}-{ts_compact}.json"
    sha_path = Path(str(plan_path) + ".sha256")

    plan_path.write_text(canonical.decode("utf-8") + "\n", encoding="utf-8")
    sha_path.write_text(digest + "\n", encoding="utf-8")

    print(f"[PASS] Plan created: {plan_path.relative_to(REPO_ROOT)}")
    print(f"[PASS] Hash file created: {sha_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
