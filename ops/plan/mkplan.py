#!/usr/bin/env python3
"""Create deterministic plan files with canonical JSON hashing."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.client
import json
import os
import re
import socket
import ssl
import subprocess
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PLANS_DIR = REPO_ROOT / "plans"
CORE_CONTAINER_NAMES = ("core-postgres-1", "core-minio-1", "core-vaultwarden-1")
CORE_HEALTH_TIMEOUT_SECONDS = 120
CORE_HEALTH_POLL_INTERVAL_SECONDS = 2
CORE_COMPOSE_CANDIDATES = (
    REPO_ROOT / "bootstrap" / "compose" / "core" / "docker-compose.yml",
    REPO_ROOT / "bootstrap" / "compose" / "core" / "docker-compose.yaml",
    REPO_ROOT / "bootstrap" / "compose" / "core" / "compose.yml",
    REPO_ROOT / "bootstrap" / "compose" / "core" / "compose.yaml",
)
RESTIC_BUCKET_NAME = "cortex-restic"
RESTIC_REPOSITORY_DEFAULT = f"s3:http://minio:9000/{RESTIC_BUCKET_NAME}"
LOGS_DIR = REPO_ROOT / "artifacts" / "logs"
REDACT_ENV_KEYS = ("MINIO_ROOT_PASSWORD", "AWS_SECRET_ACCESS_KEY", "RESTIC_PASSWORD", "MC_HOST_local")


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


def list_running_stack_containers() -> list[str]:
    output = subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"], text=True)
    return sorted(
        name.strip()
        for name in output.splitlines()
        if name.strip() and (name.startswith("core-") or name.startswith("edge-"))
    )


def list_health_configured_stack_containers(container_names: list[str]) -> list[str]:
    result: list[str] = []
    for name in container_names:
        marker = subprocess.check_output(
            ["docker", "inspect", "--format", "{{if .State.Health}}yes{{else}}no{{end}}", name],
            text=True,
        ).strip()
        if marker == "yes":
            result.append(name)
    return result


def poll_container_health(
    container_names: tuple[str, ...] | list[str],
    timeout_seconds: int = CORE_HEALTH_TIMEOUT_SECONDS,
    poll_interval_seconds: int = CORE_HEALTH_POLL_INTERVAL_SECONDS,
    label: str = "containers",
) -> int:
    names = tuple(container_names)
    if not names:
        print(f"No health-configured {label} to poll.")
        return 0
    cmd = [
        "docker",
        "inspect",
        *names,
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
            name: str(statuses[index]) if index < len(statuses) else "missing" for index, name in enumerate(names)
        }
        last_statuses = mapped
        summary = " ".join(f"{name}={status}" for name, status in mapped.items())
        print(f"health poll {attempt} ({label}): {summary}")

        if len(statuses) == len(names) and all(status == "healthy" for status in statuses):
            print(f"All {label} are healthy.")
            return 0

        if time.monotonic() >= deadline:
            print(
                f"Timed out after {timeout_seconds}s waiting for {label} health. "
                f"Last statuses: {last_statuses}"
            )
            return 1

        time.sleep(poll_interval_seconds)


def poll_core_container_health(
    timeout_seconds: int = CORE_HEALTH_TIMEOUT_SECONDS,
    poll_interval_seconds: int = CORE_HEALTH_POLL_INTERVAL_SECONDS,
) -> int:
    return poll_container_health(
        CORE_CONTAINER_NAMES,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        label="core containers",
    )


def run_stack_status_smoke_checks() -> int:
    running = list_running_stack_containers()
    if running:
        print("Stack containers:", ", ".join(running))
    else:
        print("Stack containers: none")

    health_configured = list_health_configured_stack_containers(running)
    print("Health-managed containers:", ", ".join(health_configured) if health_configured else "none")

    health_rc = poll_container_health(health_configured, label="stack health-managed containers")
    caddy_running = "edge-caddy-1" in set(running)
    print(f"Caddy running: {caddy_running}")

    if health_rc == 0 and caddy_running:
        print("STACK STATUS: PASS")
        return 0

    print("STACK STATUS: FAIL")
    return 1


def get_edge_caddy_ip() -> str:
    ip = subprocess.check_output(
        [
            "docker",
            "inspect",
            "--format",
            "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}",
            "edge-caddy-1",
        ],
        text=True,
    ).strip()
    if not ip:
        raise RuntimeError("edge-caddy-1 has no container IP")
    return ip


def run_caddy_listen_check() -> int:
    try:
        ip = get_edge_caddy_ip()
        with socket.create_connection((ip, 80), timeout=5):
            pass
        payload = {"status_code": 200, "message": f"TCP connect succeeded to {ip}:80"}
        print(json.dumps(payload, sort_keys=True))
        return 0
    except Exception as exc:
        payload = {"status_code": 503, "message": f"TCP connect failed for edge-caddy-1:80 ({exc})"}
        print(json.dumps(payload, sort_keys=True))
        return 1


def run_caddy_route_check(route: str) -> int:
    domain = os.environ.get("PUBLIC_DOMAIN", "").strip()
    if not domain:
        payload = {"status_code": 503, "message": "PUBLIC_DOMAIN is not set for route check"}
        print(json.dumps(payload, sort_keys=True))
        return 1

    host = f"{route}.{domain}"
    try:
        ip = get_edge_caddy_ip()
        conn = http.client.HTTPConnection(ip, 80, timeout=5)
        conn.request("HEAD", "/", headers={"Host": host})
        response = conn.getresponse()
        status_code = int(response.status)
        response.read()
        conn.close()
    except Exception as exc:
        payload = {"status_code": 503, "message": f"{route} route check failed to connect ({exc})"}
        print(json.dumps(payload, sort_keys=True))
        return 1

    if status_code == 404 or 500 <= status_code <= 599:
        payload = {"status_code": status_code, "message": f"{route} route check failed"}
        print(json.dumps(payload, sort_keys=True))
        return 1

    payload = {"status_code": status_code, "message": f"{route} route check passed"}
    print(json.dumps(payload, sort_keys=True))
    return 0


def check_ingress_host(route: str, timeout_seconds: int = 8) -> dict[str, object]:
    domain = os.environ.get("PUBLIC_DOMAIN", "").strip()
    if not domain:
        return {
            "route": route,
            "host": "",
            "status_code": 0,
            "server": "",
            "cf_ray": "",
            "elapsed_ms": 0,
            "passed": False,
            "message": "PUBLIC_DOMAIN is not set",
        }

    host = f"{route}.{domain}"
    started = time.monotonic()
    try:
        connection = http.client.HTTPSConnection(
            host,
            timeout=timeout_seconds,
            context=ssl.create_default_context(),
        )
        connection.request("HEAD", "/")
        response = connection.getresponse()
        status_code = int(response.status)
        server = response.getheader("server", "")
        cf_ray = response.getheader("cf-ray", "")
        response.read()
        connection.close()
    except Exception as exc:
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return {
            "route": route,
            "host": host,
            "status_code": 0,
            "server": "",
            "cf_ray": "",
            "elapsed_ms": elapsed_ms,
            "passed": False,
            "message": f"request failed ({exc})",
        }

    elapsed_ms = int((time.monotonic() - started) * 1000)
    status_ok = status_code in {200, 302, 403}
    server_ok = "cloudflare" in server.lower()
    passed = status_ok and server_ok
    message = "pass" if passed else "fail"
    return {
        "route": route,
        "host": host,
        "status_code": status_code,
        "server": server,
        "cf_ray": cf_ray,
        "elapsed_ms": elapsed_ms,
        "passed": passed,
        "message": message,
    }


def run_ingress_host_check(route: str) -> int:
    result = check_ingress_host(route)
    print(json.dumps(result, sort_keys=True))
    return 0


def run_ingress_status_summary() -> int:
    vault = check_ingress_host("vault")
    minio = check_ingress_host("minio")
    passed = bool(vault.get("passed")) and bool(minio.get("passed"))
    print(f"INGRESS STATUS: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


def redact_text(text: str, env: dict[str, str] | None = None) -> str:
    redacted = text
    for key in REDACT_ENV_KEYS:
        redacted = re.sub(rf"({re.escape(key)}\s*=\s*)\S+", r"\1***", redacted)
    secret_values: list[str] = []
    merged_env = dict(os.environ)
    if env:
        merged_env.update(env)
    for key in REDACT_ENV_KEYS:
        value = merged_env.get(key, "")
        if value:
            secret_values.append(value)
    for value in secret_values:
        redacted = redacted.replace(value, "***")
    return redacted


def tail_lines(text: str, count: int) -> str:
    lines = text.splitlines()
    if not lines:
        return "<empty>"
    return "\n".join(lines[-count:])


def create_step_log(prefix: str) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    log_path = LOGS_DIR / f"{prefix}-{stamp}.log"
    log_path.write_text("", encoding="utf-8")
    return log_path


def append_step_log(log_path: Path, content: str) -> None:
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(content)
        if not content.endswith("\n"):
            handle.write("\n")


def run_step(
    step_name: str,
    argv: list[str],
    *,
    log_path: Path,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int | None = None,
) -> bool:
    completed = run_step_capture(
        step_name,
        argv,
        log_path=log_path,
        env=env,
        cwd=cwd,
        timeout=timeout,
        fail_on_nonzero=True,
    )
    return completed is not None


def run_step_capture(
    step_name: str,
    argv: list[str],
    *,
    log_path: Path,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    timeout: int | None = None,
    fail_on_nonzero: bool = True,
) -> subprocess.CompletedProcess[str] | None:
    print(f"[STEP] {step_name}")
    append_step_log(log_path, f"[STEP] {step_name}")
    append_step_log(log_path, f"CMD: {' '.join(argv)}")
    if cwd is not None:
        append_step_log(log_path, f"CWD: {cwd}")
    try:
        completed = subprocess.run(
            argv,
            env=env,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=False,
        )
    except Exception as exc:
        message = redact_text(str(exc), env)
        print(f"[STEP-FAIL] {step_name} exit=exception")
        print(f"CMD: {' '.join(argv)}")
        print("STDOUT (tail 40):")
        print("<empty>")
        print("STDERR (tail 80):")
        print(message)
        append_step_log(log_path, f"[STEP-FAIL] {step_name} exit=exception")
        append_step_log(log_path, "STDOUT (tail 40):\n<empty>")
        append_step_log(log_path, f"STDERR (tail 80):\n{message}")
        return None

    stdout_text = redact_text(completed.stdout or "", env)
    stderr_text = redact_text(completed.stderr or "", env)
    append_step_log(log_path, f"exit={completed.returncode}")
    append_step_log(log_path, f"STDOUT:\n{stdout_text if stdout_text else '<empty>'}")
    append_step_log(log_path, f"STDERR:\n{stderr_text if stderr_text else '<empty>'}")

    if completed.returncode != 0 and fail_on_nonzero:
        print(f"[STEP-FAIL] {step_name} exit={completed.returncode}")
        print(f"CMD: {' '.join(argv)}")
        print("STDOUT (tail 40):")
        print(tail_lines(stdout_text, 40))
        print("STDERR (tail 80):")
        print(tail_lines(stderr_text, 80))
        append_step_log(log_path, f"[STEP-FAIL] {step_name} exit={completed.returncode}")
        append_step_log(log_path, f"STDOUT (tail 40):\n{tail_lines(stdout_text, 40)}")
        append_step_log(log_path, f"STDERR (tail 80):\n{tail_lines(stderr_text, 80)}")
        return None
    return completed


def get_core_compose_file() -> Path:
    for candidate in CORE_COMPOSE_CANDIDATES:
        if candidate.is_file():
            return candidate
    raise RuntimeError("Core compose file not found under bootstrap/compose/core")


def get_core_network_name() -> str:
    for container_name in ("core-minio-1", "core-postgres-1", "core-vaultwarden-1"):
        inspect = subprocess.run(
            ["docker", "inspect", "--format", "{{json .NetworkSettings.Networks}}", container_name],
            capture_output=True,
            text=True,
            check=False,
        )
        if inspect.returncode != 0:
            continue
        payload = inspect.stdout.strip()
        if not payload:
            continue
        parsed = json.loads(payload)
        if isinstance(parsed, dict) and parsed:
            return sorted(parsed.keys())[0]
    raise RuntimeError("Could not determine core docker network from running core containers")


def ensure_minio_available() -> None:
    status = subprocess.check_output(
        ["docker", "inspect", "--format", "{{.State.Status}}", "core-minio-1"],
        text=True,
    ).strip()
    if status != "running":
        raise RuntimeError(f"core-minio-1 is not running (status={status})")

    health_status = subprocess.check_output(
        [
            "docker",
            "inspect",
            "--format",
            "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}",
            "core-minio-1",
        ],
        text=True,
    ).strip()
    if health_status in {"none", "healthy"}:
        return
    if poll_container_health(["core-minio-1"], label="minio") != 0:
        raise RuntimeError(f"core-minio-1 health check failed (status={health_status})")


def run_backup_core() -> int:
    log_path = create_step_log("backup-core")
    compose_file = get_core_compose_file()
    network_name = get_core_network_name()
    minio_user = os.environ.get("MINIO_ROOT_USER", "").strip()
    minio_password = os.environ.get("MINIO_ROOT_PASSWORD", "").strip()
    restic_password = os.environ.get("RESTIC_PASSWORD", "").strip()
    if not minio_user or not minio_password or not restic_password:
        print("BACKUP-CORE: FAIL")
        return 1

    restic_repository = os.environ.get("RESTIC_REPOSITORY", RESTIC_REPOSITORY_DEFAULT).strip()
    run_env = os.environ.copy()
    run_env.update(
        {
            "MINIO_ROOT_USER": minio_user,
            "MINIO_ROOT_PASSWORD": minio_password,
            "AWS_ACCESS_KEY_ID": minio_user,
            "AWS_SECRET_ACCESS_KEY": minio_password,
            "RESTIC_PASSWORD": restic_password,
            "RESTIC_REPOSITORY": restic_repository,
            "MC_HOST_local": f"http://{minio_user}:{minio_password}@minio:9000",
        }
    )
    stopped = False
    success = True

    success = run_step(
        "ensure-restic-bucket-alias",
        [
            "docker",
            "run",
            "--rm",
            "--network",
            network_name,
            "-e",
            "MINIO_ROOT_USER",
            "-e",
            "MINIO_ROOT_PASSWORD",
            "minio/mc",
            "alias",
            "set",
            "local",
            "http://minio:9000",
            minio_user,
            minio_password,
        ],
        env=run_env,
        log_path=log_path,
    )
    if success:
        success = run_step(
            "ensure-restic-bucket-mkdir",
            [
                "docker",
                "run",
                "--rm",
                "--network",
                network_name,
                "-e",
                "MINIO_ROOT_USER",
                "-e",
                "MINIO_ROOT_PASSWORD",
                "-e",
                "MC_HOST_local",
                "minio/mc",
                "mb",
                "--ignore-existing",
                f"local/{RESTIC_BUCKET_NAME}",
            ],
            env=run_env,
            log_path=log_path,
        )
    if success:
        success = run_step(
            "stop-postgres-vaultwarden",
            [
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "stop",
                "postgres",
                "vaultwarden",
            ],
            cwd=REPO_ROOT,
            log_path=log_path,
        )
        stopped = success

    if success:
        print("[STEP] ensure-minio-available")
        append_step_log(log_path, "[STEP] ensure-minio-available")
        try:
            ensure_minio_available()
        except Exception as exc:
            message = redact_text(str(exc), run_env)
            print("[STEP-FAIL] ensure-minio-available exit=exception")
            print("CMD: python3 -c ensure_minio_available")
            print("STDOUT (tail 40):")
            print("<empty>")
            print("STDERR (tail 80):")
            print(message)
            append_step_log(log_path, "[STEP-FAIL] ensure-minio-available exit=exception")
            append_step_log(log_path, f"STDERR (tail 80):\n{message}")
            success = False

    if success:
        restic_argv_prefix = [
            "docker",
            "run",
            "--rm",
            "--network",
            network_name,
            "-e",
            "RESTIC_REPOSITORY",
            "-e",
            "AWS_ACCESS_KEY_ID",
            "-e",
            "AWS_SECRET_ACCESS_KEY",
            "-e",
            "RESTIC_PASSWORD",
            "-v",
            "postgres_data:/src/postgres:ro",
            "-v",
            "minio_data:/src/minio:ro",
            "-v",
            "vaultwarden_data:/src/vaultwarden:ro",
            "restic/restic",
        ]
        snapshots_result = run_step_capture(
            "restic-snapshots",
            [*restic_argv_prefix, "snapshots"],
            env=run_env,
            log_path=log_path,
            fail_on_nonzero=False,
        )
        if snapshots_result is None:
            success = False
        elif snapshots_result.returncode != 0:
            combined = f"{snapshots_result.stdout}\n{snapshots_result.stderr}"
            if "Is there a repository at the following location?" in combined:
                success = run_step(
                    "restic-init",
                    [*restic_argv_prefix, "init"],
                    env=run_env,
                    log_path=log_path,
                )
            else:
                stdout_text = redact_text(snapshots_result.stdout or "", run_env)
                stderr_text = redact_text(snapshots_result.stderr or "", run_env)
                print(f"[STEP-FAIL] restic-snapshots exit={snapshots_result.returncode}")
                print(f"CMD: {' '.join([*restic_argv_prefix, 'snapshots'])}")
                print("STDOUT (tail 40):")
                print(tail_lines(stdout_text, 40))
                print("STDERR (tail 80):")
                print(tail_lines(stderr_text, 80))
                append_step_log(
                    log_path, f"[STEP-FAIL] restic-snapshots exit={snapshots_result.returncode}"
                )
                append_step_log(log_path, f"STDOUT (tail 40):\n{tail_lines(stdout_text, 40)}")
                append_step_log(log_path, f"STDERR (tail 80):\n{tail_lines(stderr_text, 80)}")
                success = False

    if success:
        success = run_step(
            "restic-backup",
            [
                *restic_argv_prefix,
                "backup",
                "/src",
                "--tag",
                "core",
                "--host",
                "majelis",
            ],
            env=run_env,
            log_path=log_path,
        )

    if stopped:
        start_ok = run_step(
            "start-postgres-vaultwarden",
            [
                "docker",
                "compose",
                "-f",
                str(compose_file),
                "up",
                "-d",
                "postgres",
                "vaultwarden",
            ],
            cwd=REPO_ROOT,
            log_path=log_path,
        )
        success = success and start_ok

    print(f"[INFO] Step log: {log_path.relative_to(REPO_ROOT)}")
    if success:
        print("BACKUP-CORE: PASS")
        return_code = 0
    else:
        print("BACKUP-CORE: FAIL")
        return_code = 1
    return return_code


def run_restore_test() -> int:
    log_path = create_step_log("restore-test")
    network_name = get_core_network_name()
    minio_user = os.environ.get("MINIO_ROOT_USER", "").strip()
    minio_password = os.environ.get("MINIO_ROOT_PASSWORD", "").strip()
    restic_password = os.environ.get("RESTIC_PASSWORD", "").strip()
    if not minio_user or not minio_password or not restic_password:
        print("RESTORE-TEST: FAIL")
        return 1

    restic_repository = os.environ.get("RESTIC_REPOSITORY", RESTIC_REPOSITORY_DEFAULT).strip()
    restore_timestamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    restore_root = REPO_ROOT / "artifacts" / "restore-test" / restore_timestamp
    restore_root.mkdir(parents=True, exist_ok=True)
    run_env = os.environ.copy()
    run_env.update(
        {
            "AWS_ACCESS_KEY_ID": minio_user,
            "AWS_SECRET_ACCESS_KEY": minio_password,
            "RESTIC_PASSWORD": restic_password,
            "RESTIC_REPOSITORY": restic_repository,
        }
    )

    ok = run_step(
        "restic-restore-latest",
        [
            "docker",
            "run",
            "--rm",
            "--network",
            network_name,
            "-e",
            "RESTIC_REPOSITORY",
            "-e",
            "AWS_ACCESS_KEY_ID",
            "-e",
            "AWS_SECRET_ACCESS_KEY",
            "-e",
            "RESTIC_PASSWORD",
            "-v",
            f"{restore_root}:/restore",
            "restic/restic",
            "restore",
            "latest",
            "--target",
            "/restore",
        ],
        env=run_env,
        log_path=log_path,
    )
    if not ok:
        print(f"[INFO] Step log: {log_path.relative_to(REPO_ROOT)}")
        print("RESTORE-TEST: FAIL")
        return 1

    vaultwarden_file = restore_root / "src" / "vaultwarden" / "db.sqlite3"
    postgres_version = restore_root / "src" / "postgres" / "PG_VERSION"
    minio_path = restore_root / "src" / "minio"
    minio_non_empty = minio_path.is_dir() and any(minio_path.iterdir())
    if not vaultwarden_file.is_file():
        append_step_log(log_path, f"[STEP-FAIL] verify-vaultwarden-db missing {vaultwarden_file}")
        print("[STEP-FAIL] verify-vaultwarden-db exit=1")
        print("CMD: local file existence check")
        print("STDOUT (tail 40):")
        print("<empty>")
        print("STDERR (tail 80):")
        print(f"missing file: {vaultwarden_file}")
        print(f"[INFO] Step log: {log_path.relative_to(REPO_ROOT)}")
        print("RESTORE-TEST: FAIL")
        return 1
    if not postgres_version.is_file():
        append_step_log(log_path, f"[STEP-FAIL] verify-postgres-version missing {postgres_version}")
        print("[STEP-FAIL] verify-postgres-version exit=1")
        print("CMD: local file existence check")
        print("STDOUT (tail 40):")
        print("<empty>")
        print("STDERR (tail 80):")
        print(f"missing file: {postgres_version}")
        print(f"[INFO] Step log: {log_path.relative_to(REPO_ROOT)}")
        print("RESTORE-TEST: FAIL")
        return 1
    if not minio_non_empty:
        append_step_log(log_path, f"[STEP-FAIL] verify-minio-non-empty missing/non-empty {minio_path}")
        print("[STEP-FAIL] verify-minio-non-empty exit=1")
        print("CMD: local directory non-empty check")
        print("STDOUT (tail 40):")
        print("<empty>")
        print("STDERR (tail 80):")
        print(f"minio restore path is empty or missing: {minio_path}")
        print(f"[INFO] Step log: {log_path.relative_to(REPO_ROOT)}")
        print("RESTORE-TEST: FAIL")
        return 1

    append_step_log(log_path, "[STEP] verify-restore-tree PASS")
    print(f"[INFO] Step log: {log_path.relative_to(REPO_ROOT)}")
    print("RESTORE-TEST: PASS")
    return 0


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


def build_stack_status_plan(created_at: str) -> dict:
    list_stack_script = (
        "import subprocess;"
        "out=subprocess.check_output(['docker','ps','--format','{{.Names}} {{.Status}}'],text=True).splitlines();"
        "filtered=[line for line in out if line.startswith('core-') or line.startswith('edge-')];"
        "print('\\n'.join(filtered) if filtered else 'No core-/edge- containers are running.')"
    )
    stack_smoke_script = (
        "from ops.plan.mkplan import run_stack_status_smoke_checks;"
        "raise SystemExit(run_stack_status_smoke_checks())"
    )
    caddy_listen_script = (
        "from ops.plan.mkplan import run_caddy_listen_check;"
        "raise SystemExit(run_caddy_listen_check())"
    )
    route_vault_script = (
        "from ops.plan.mkplan import run_caddy_route_check;"
        "raise SystemExit(run_caddy_route_check('vault'))"
    )
    route_minio_script = (
        "from ops.plan.mkplan import run_caddy_route_check;"
        "raise SystemExit(run_caddy_route_check('minio'))"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "stack-ps-core-edge",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", list_stack_script],
                "destructive": False,
            },
            {
                "id": "stack-smoke",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", stack_smoke_script],
                "destructive": False,
            },
            {
                "id": "caddy_listen_check",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", caddy_listen_script],
                "destructive": False,
            },
            {
                "id": "route_check_vault",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", route_vault_script],
                "destructive": False,
            },
            {
                "id": "route_check_minio",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", route_minio_script],
                "destructive": False,
            },
        ],
    }


def build_ingress_status_plan(created_at: str) -> dict:
    vault_script = (
        "from ops.plan.mkplan import run_ingress_host_check;"
        "raise SystemExit(run_ingress_host_check('vault'))"
    )
    minio_script = (
        "from ops.plan.mkplan import run_ingress_host_check;"
        "raise SystemExit(run_ingress_host_check('minio'))"
    )
    summary_script = (
        "from ops.plan.mkplan import run_ingress_status_summary;"
        "raise SystemExit(run_ingress_status_summary())"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "ingress_check_vault",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", vault_script],
                "destructive": False,
            },
            {
                "id": "ingress_check_minio",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", minio_script],
                "destructive": False,
            },
            {
                "id": "ingress_status_summary",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", summary_script],
                "destructive": False,
            },
        ],
    }


def build_backup_core_plan(created_at: str) -> dict:
    backup_script = (
        "from ops.plan.mkplan import run_backup_core;"
        "raise SystemExit(run_backup_core())"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "backup-core",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", backup_script],
                "destructive": True,
            }
        ],
    }


def build_restore_test_plan(created_at: str) -> dict:
    restore_script = (
        "from ops.plan.mkplan import run_restore_test;"
        "raise SystemExit(run_restore_test())"
    )
    return {
        "version": 1,
        "created_at": created_at,
        "env": "dev",
        "target": "majelis",
        "actions": [
            {
                "id": "restore-test",
                "type": "shell",
                "cwd": ".",
                "cmd": ["python3", "-c", restore_script],
                "destructive": False,
            }
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
            "stack-status",
            "ingress-status",
            "backup-core",
            "restore-test",
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
    elif args.template == "stack-status":
        plan = build_stack_status_plan(created_at)
    elif args.template == "ingress-status":
        plan = build_ingress_status_plan(created_at)
    elif args.template == "backup-core":
        plan = build_backup_core_plan(created_at)
    elif args.template == "restore-test":
        plan = build_restore_test_plan(created_at)
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
