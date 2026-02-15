#!/usr/bin/env python3
"""Create deterministic plan files with canonical JSON hashing."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLANS_DIR = REPO_ROOT / "plans"
CORE_CONTAINER_NAMES = ("core-postgres-1", "core-minio-1", "core-vaultwarden-1")
CORE_HEALTH_TIMEOUT_SECONDS = 120
CORE_HEALTH_POLL_INTERVAL_SECONDS = 2


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


def poll_core_container_health(
    timeout_seconds: int = CORE_HEALTH_TIMEOUT_SECONDS,
    poll_interval_seconds: int = CORE_HEALTH_POLL_INTERVAL_SECONDS,
) -> int:
    cmd = [
        "docker",
        "inspect",
        *CORE_CONTAINER_NAMES,
        "--format",
        "{{json .State.Health.Status}}",
    ]
    deadline = time.monotonic() + timeout_seconds
    attempt = 0
    last_statuses: dict[str, str] = {}

    while True:
        attempt += 1
        output = subprocess.check_output(cmd, text=True)
        statuses = [json.loads(line) for line in output.splitlines() if line.strip()]
        mapped = {
            name: str(statuses[index]) if index < len(statuses) else "missing"
            for index, name in enumerate(CORE_CONTAINER_NAMES)
        }
        last_statuses = mapped
        summary = " ".join(f"{name}={status}" for name, status in mapped.items())
        print(f"health poll {attempt}: {summary}")

        if len(statuses) == len(CORE_CONTAINER_NAMES) and all(status == "healthy" for status in statuses):
            print("Core containers are healthy.")
            return 0

        if time.monotonic() >= deadline:
            print(
                f"Timed out after {timeout_seconds}s waiting for core container health. "
                f"Last statuses: {last_statuses}"
            )
            return 1

        time.sleep(poll_interval_seconds)


def build_bootstrap_core_up_plan(created_at: str) -> dict:
    health_check_script = (
        "from ops.plan.mkplan import poll_core_container_health;"
        "raise SystemExit(poll_core_container_health())"
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


def build_edge_dry_run_plan(created_at: str) -> dict:
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "local-repo",
        "actions": [
            {
                "id": "edge-compose-config",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/edge",
                "args": ["config"],
                "destructive": False,
            }
        ],
    }


def build_edge_up_plan(created_at: str) -> dict:
    verify_up_script = (
        "import subprocess,sys;"
        "target={'edge-cloudflared-1','edge-caddy-1'};"
        "out=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}'],text=True).splitlines();"
        "names={line.split(' ',1)[0] for line in out if line.strip()};"
        "missing=sorted(target - names);"
        "print('\\n'.join(out));"
        "sys.exit(0 if not missing else 1)"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "edge-up",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/edge",
                "args": ["up", "-d"],
                "destructive": False,
            },
            {
                "id": "edge-verify-up",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", verify_up_script],
                "destructive": False,
            },
        ],
    }


def build_edge_down_plan(created_at: str) -> dict:
    verify_down_script = (
        "import subprocess,sys;"
        "target={'edge-cloudflared-1','edge-caddy-1'};"
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
                "id": "edge-down",
                "type": "docker_compose",
                "project_dir": "bootstrap/compose/edge",
                "args": ["down"],
                "destructive": False,
            },
            {
                "id": "edge-verify-down",
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
            "edge-dry-run",
            "edge-up",
            "edge-down",
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
    elif args.template == "edge-dry-run":
        plan = build_edge_dry_run_plan(created_at)
    elif args.template == "edge-up":
        plan = build_edge_up_plan(created_at)
    elif args.template == "edge-down":
        plan = build_edge_down_plan(created_at)
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
