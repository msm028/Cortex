#!/usr/bin/env python3
"""Generate a wiki-friendly operations status page from local repo artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def now_local_stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d %H:%M")


def newest_file(paths: list[Path]) -> Path | None:
    if not paths:
        return None
    return sorted(paths, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def newest_status_snapshot(root: Path) -> dict[str, Any] | None:
    snapshot_dir = root / "artifacts" / "status"
    path = newest_file(list(snapshot_dir.glob("uptime-kuma-live*.json")) + list(snapshot_dir.glob("uptime-kuma-live.json")))
    if path is None:
        return None
    try:
        payload = read_json(path)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    payload["_path"] = str(path.relative_to(root))
    return payload


def extract_status_from_log(path: Path, prefix: str) -> str:
    for line in reversed(path.read_text(encoding="utf-8", errors="replace").splitlines()):
        line = line.strip()
        if line.startswith(prefix):
            return line.split(":", 1)[1].strip()
    return "UNKNOWN"


def latest_plan(root: Path) -> dict[str, str]:
    path = newest_file(list((root / "plans").glob("*.json")))
    if path is None:
        return {"name": "<none>", "path": "<none>", "mtime": "<none>"}
    return {
        "name": path.name,
        "path": str(path.relative_to(root)),
        "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    }


def latest_audit(root: Path) -> dict[str, str]:
    path = newest_file(list((root / "artifacts" / "audit").glob("*.audit.json")))
    if path is None:
        return {"name": "<none>", "plan": "<none>", "status": "<none>", "executed_at": "<none>"}
    payload = read_json(path)
    return {
        "name": path.name,
        "plan": str(payload.get("plan", "<none>")),
        "status": str(payload.get("status", "<none>")).upper(),
        "executed_at": str(payload.get("executed_at", "<none>")),
    }


def latest_action_audit(root: Path, needle: str) -> dict[str, str]:
    matches: list[Path] = []
    for path in (root / "artifacts" / "audit").glob("*.audit.json"):
        try:
            payload = read_json(path)
        except Exception:
            continue
        plan = str(payload.get("plan", ""))
        action_ids = [
            str(item.get("id", ""))
            for item in payload.get("action_results", [])
            if isinstance(item, dict)
        ]
        if needle in plan or needle in action_ids:
            matches.append(path)
    newest = newest_file(matches)
    if newest is None:
        return {"name": "<none>", "status": "<none>", "executed_at": "<none>"}
    payload = read_json(newest)
    return {
        "name": newest.name,
        "status": str(payload.get("status", "<none>")).upper(),
        "executed_at": str(payload.get("executed_at", "<none>")),
    }


def latest_action_log(root: Path, stem: str, prefix: str) -> dict[str, str]:
    path = newest_file(list((root / "artifacts" / "logs").glob(f"{stem}-*.log")))
    if path is None:
        return {"name": "<none>", "status": "<none>", "mtime": "<none>"}
    return {
        "name": path.name,
        "status": extract_status_from_log(path, prefix),
        "mtime": dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
    }


def action_summary(log_info: dict[str, str], audit_info: dict[str, str]) -> dict[str, str]:
    if log_info.get("status") == "UNKNOWN":
        audit_status = audit_info.get("status", "")
        if audit_status == "PASSED":
            log_info = {**log_info, "status": "PASS"}
        elif audit_status == "FAILED":
            log_info = {**log_info, "status": "FAIL"}
    return log_info


def inventory_endpoints(root: Path) -> list[str]:
    path = root / "docs" / "inventory.md"
    if not path.is_file():
        return []
    lines = path.read_text(encoding="utf-8").splitlines()
    capture = False
    endpoints: list[str] = []
    for line in lines:
        if line.startswith("## Endpoints"):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture and line.startswith("- "):
            endpoints.append(line[2:].strip())
    return endpoints


def render_monitor_state(status: int | None) -> str:
    mapping = {
        0: "DOWN",
        1: "UP",
        2: "PENDING",
        3: "MAINTENANCE",
    }
    if status is None:
        return "UNKNOWN"
    return mapping.get(status, f"STATUS_{status}")


def render_status_page(root: Path) -> str:
    plan = latest_plan(root)
    audit = latest_audit(root)
    backup_audit = latest_action_audit(root, "backup-core")
    backup_log = latest_action_log(root, "backup-core", "BACKUP-CORE:")
    restore_audit = latest_action_audit(root, "restore-test")
    restore_log = latest_action_log(root, "restore-test", "RESTORE-TEST:")
    backup_log = action_summary(backup_log, backup_audit)
    restore_log = action_summary(restore_log, restore_audit)
    endpoints = inventory_endpoints(root)
    live_health = newest_status_snapshot(root)
    live_summary = "UNKNOWN"
    if live_health and isinstance(live_health.get("monitors"), list):
        states = [render_monitor_state(item.get("status")) for item in live_health["monitors"] if isinstance(item, dict) and item.get("present")]
        if states and all(state == "UP" for state in states):
            live_summary = "UP"
        elif any(state == "DOWN" for state in states):
            live_summary = "DEGRADED"
        elif states:
            live_summary = ", ".join(sorted(set(states)))

    lines = [
        "# Ops Status",
        "",
        f"Generated: {now_local_stamp()} (local)",
        "",
        "## Summary",
        "",
        "| Item | Value |",
        "| --- | --- |",
        f"| Latest plan | `{plan['name']}` |",
        f"| Latest audit status | `{audit['status']}` |",
        f"| Latest backup status | `{backup_log['status']}` |",
        f"| Latest restore-test status | `{restore_log['status']}` |",
        f"| Live health | `{live_summary}` |",
        "",
        "## Latest Plan",
        "",
        f"- File: `{plan['name']}`",
        f"- Path: `{plan['path']}`",
        f"- Modified: `{plan['mtime']}`",
        "",
        "## Latest Audit",
        "",
        f"- File: `{audit['name']}`",
        f"- Plan: `{audit['plan']}`",
        f"- Status: `{audit['status']}`",
        f"- Executed at: `{audit['executed_at']}`",
        "",
        "## Backup Status",
        "",
        f"- Latest backup audit: `{backup_audit['name']}`",
        f"- Audit status: `{backup_audit['status']}`",
        f"- Audit executed at: `{backup_audit['executed_at']}`",
        f"- Latest backup log: `{backup_log['name']}`",
        f"- Log status: `{backup_log['status']}`",
        f"- Log modified: `{backup_log['mtime']}`",
        "",
        "## Restore Test Status",
        "",
        f"- Latest restore audit: `{restore_audit['name']}`",
        f"- Audit status: `{restore_audit['status']}`",
        f"- Audit executed at: `{restore_audit['executed_at']}`",
        f"- Latest restore log: `{restore_log['name']}`",
        f"- Log status: `{restore_log['status']}`",
        f"- Log modified: `{restore_log['mtime']}`",
        "",
        "## Live Health",
        "",
    ]
    if live_health and isinstance(live_health.get("monitors"), list):
        lines.extend(
            [
                f"- Source: `{live_health.get('_path', '<none>')}`",
                f"- Generated at: `{live_health.get('generated_at', '<none>')}`",
                "",
                "| Monitor | Present | Active | State | URL |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for item in live_health["monitors"]:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"| `{item.get('name', '<none>')}` | "
                f"`{'yes' if item.get('present') else 'no'}` | "
                f"`{'yes' if item.get('active') else 'no'}` | "
                f"`{render_monitor_state(item.get('status'))}` | "
                f"`{item.get('url', '')}` |"
            )
        lines.append("")
    else:
        lines.extend(
            [
                "- Source: `<none>`",
                "- Run `make vw-run CMD=\"make uptime-kuma-verify\"` to refresh the live snapshot.",
                "",
            ]
        )

    lines.extend(
        [
        "## Key Endpoints",
        "",
        ]
    )
    if endpoints:
        lines.extend([f"- {item}" for item in endpoints])
    else:
        lines.append("- <none>")
    lines.extend(
        [
            "",
            "## Source Paths",
            "",
            "- Plans: `plans/`",
            "- Audits: `artifacts/audit/`",
            "- Step logs: `artifacts/logs/`",
            "- Inventory: `docs/inventory.md`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate docs/ops-status.md from local repo artifacts")
    parser.add_argument("--output", help="Override output path")
    args = parser.parse_args()

    root = repo_root()
    output = Path(args.output) if args.output else root / "docs" / "ops-status.md"
    if not output.is_absolute():
        output = root / output
    output.write_text(render_status_page(root), encoding="utf-8")
    print(f"[PASS] wrote {output.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
