#!/usr/bin/env python3
"""Detect local TCP port conflicts."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_PORTS = [80, 443, 8000, 3000, 8080, 9000, 9001, 9090, 5432, 6379, 8443]


def parse_ports(raw: str) -> list[int]:
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    ports: list[int] = []
    for item in parts:
        value = int(item)
        if value < 1 or value > 65535:
            raise ValueError(f"Port out of range: {value}")
        ports.append(value)
    return sorted(set(ports))


def scan_with_ss() -> dict[int, str]:
    cmd = ["ss", "-H", "-ltnp"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "ss failed")
    used: dict[int, str] = {}
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        m = re.search(r":(\d+)$", local)
        if not m:
            continue
        port = int(m.group(1))
        proc = ""
        if len(parts) >= 6:
            proc = parts[-1]
        if not proc:
            proc = "unknown"
        used[port] = proc
    return used


def scan_with_lsof() -> dict[int, str]:
    cmd = ["lsof", "-nP", "-iTCP", "-sTCP:LISTEN"]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0 and not result.stdout.strip():
        raise RuntimeError(result.stderr.strip() or "lsof failed")
    used: dict[int, str] = {}
    lines = result.stdout.splitlines()
    for line in lines[1:]:
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 9:
            continue
        cmd_name = parts[0]
        pid = parts[1]
        name_col = parts[8]
        m = re.search(r":(\d+)->|:(\d+)$", name_col)
        port_text = ""
        if m:
            port_text = m.group(1) or m.group(2) or ""
        if not port_text:
            continue
        port = int(port_text)
        used[port] = f"{cmd_name}[{pid}]"
    return used


def detect_used_ports() -> tuple[str, dict[int, str]]:
    if shutil.which("ss"):
        return "ss", scan_with_ss()
    if shutil.which("lsof"):
        return "lsof", scan_with_lsof()
    raise RuntimeError("Neither 'ss' nor 'lsof' is available")


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def load_registry_ports(root: Path) -> list[int]:
    registry = root / "docs" / "runbooks" / "ports-registry.yaml"
    if not registry.is_file():
        return []
    text = registry.read_text(encoding="utf-8", errors="replace")
    hits = re.findall(r"^\s*(?:-\s*)?port:\s*(\d+)\s*$", text, flags=re.MULTILINE)
    ports: list[int] = []
    for raw in hits:
        value = int(raw)
        if 1 <= value <= 65535:
            ports.append(value)
    return sorted(set(ports))


def build_result(
    ports: list[int], used: dict[int, str], source: str, defaults_source: str | None = None
) -> dict[str, Any]:
    items = []
    for port in ports:
        in_use = port in used
        items.append(
            {
                "port": port,
                "status": "IN-USE" if in_use else "FREE",
                "process": used.get(port, ""),
            }
        )
    payload = {"source": source, "ports": items}
    if defaults_source:
        payload["defaults_source"] = defaults_source
    return payload


def print_pretty(result: dict[str, Any]) -> None:
    print(f"source: {result['source']}")
    if "defaults_source" in result:
        print(f"[INFO] defaults source: {result['defaults_source']}")
    for item in result["ports"]:
        if item["status"] == "IN-USE":
            print(f"{item['port']}: IN-USE ({item['process'] or 'unknown'})")
        else:
            print(f"{item['port']}: FREE")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check local TCP port usage")
    parser.add_argument("--ports", help='Comma-separated list, e.g. "8000,5432,9000"')
    parser.add_argument("--defaults", action="store_true", help="Use built-in default port list")
    parser.add_argument("--fail-on-used", action="store_true", help="Exit non-zero if any checked port is used")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    defaults_source: str | None = None
    if args.ports:
        ports = parse_ports(args.ports)
    else:
        root = repo_root()
        registry_ports = load_registry_ports(root)
        if registry_ports:
            ports = registry_ports
            defaults_source = "registry"
        else:
            ports = DEFAULT_PORTS
            defaults_source = "built-in"

    if args.defaults and defaults_source is None:
        # explicit defaults while --ports is not provided follows default behavior
        defaults_source = "registry" if ports != DEFAULT_PORTS else "built-in"

    if not ports:
        ports = DEFAULT_PORTS
        defaults_source = "built-in"

    try:
        source, used = detect_used_ports()
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1

    result = build_result(ports, used, source, defaults_source)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print_pretty(result)

    if args.fail_on_used and any(item["status"] == "IN-USE" for item in result["ports"]):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
