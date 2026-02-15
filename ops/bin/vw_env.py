#!/usr/bin/env python3
"""Vaultwarden environment injector using Bitwarden CLI."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import shutil
import subprocess
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
MAP_PATH = REPO_ROOT / "ops" / "env" / "vaultwarden-map.json"


def load_mapping() -> dict[str, dict[str, str]]:
    if not MAP_PATH.is_file():
        raise RuntimeError(f"mapping file missing: {MAP_PATH}")
    try:
        payload = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"mapping file is invalid json: {exc}") from exc
    if not isinstance(payload, dict) or not payload:
        raise RuntimeError("mapping file must be a non-empty object")
    normalized: dict[str, dict[str, str]] = {}
    for var_name, entry in payload.items():
        if not isinstance(var_name, str):
            raise RuntimeError("mapping keys must be environment variable names")
        if not isinstance(entry, dict):
            raise RuntimeError(f"mapping entry for {var_name} must be an object")
        item_id = entry.get("item_id")
        source = entry.get("source")
        if not isinstance(item_id, str) or not isinstance(source, str):
            raise RuntimeError(f"mapping entry for {var_name} must include string item_id/source")
        normalized[var_name] = {"item_id": item_id, "source": source}
    return normalized


def source_is_valid(source: str) -> bool:
    return source in {"login.username", "login.password"} or source.startswith("field:")


def preflight_errors(mapping: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    if shutil.which("bw") is None:
        errors.append("Bitwarden CLI not found. Install 'bw' and ensure it is on PATH.")
    if not os.environ.get("BW_SESSION", "").strip():
        errors.append("BW_SESSION is not set. Run 'bw unlock --raw' and export BW_SESSION.")
    for var_name, entry in mapping.items():
        item_id = entry.get("item_id", "").strip()
        source = entry.get("source", "").strip()
        if not item_id or item_id == "REPLACE_ME":
            errors.append(f"{var_name} mapping has no real item_id.")
        if not source_is_valid(source):
            errors.append(f"{var_name} mapping source is invalid: {source}")
    return errors


def print_mapping_status(mapping: dict[str, dict[str, str]]) -> bool:
    missing = False
    for var_name, entry in mapping.items():
        item_id = entry.get("item_id", "").strip()
        source = entry.get("source", "").strip()
        if item_id and item_id != "REPLACE_ME" and source_is_valid(source):
            print(f"{var_name}: OK")
        else:
            print(f"{var_name}: MISSING")
            missing = True
    return not missing


def fetch_item(item_id: str) -> dict[str, Any]:
    result = subprocess.run(
        ["bw", "get", "item", item_id],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"bw get item failed for item_id={item_id}: {stderr or 'unknown error'}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"bw returned invalid json for item_id={item_id}") from exc
    if not isinstance(payload, dict):
        raise RuntimeError(f"bw returned unexpected payload for item_id={item_id}")
    return payload


def extract_value(item: dict[str, Any], source: str) -> str:
    if source == "login.username":
        login = item.get("login", {})
        value = login.get("username") if isinstance(login, dict) else None
    elif source == "login.password":
        login = item.get("login", {})
        value = login.get("password") if isinstance(login, dict) else None
    elif source.startswith("field:"):
        field_name = source.split(":", 1)[1]
        value = None
        fields = item.get("fields", [])
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict) and field.get("name") == field_name:
                    value = field.get("value")
                    break
    else:
        value = None
    if not isinstance(value, str) or not value:
        raise RuntimeError(f"source value missing for {source}")
    return value


def run_check() -> int:
    try:
        mapping = load_mapping()
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    mapping_ok = print_mapping_status(mapping)
    errors = preflight_errors(mapping)
    for err in errors:
        print(f"[FAIL] {err}")

    if mapping_ok and not errors:
        print("VW-CHECK: PASS")
        return 0
    print("VW-CHECK: FAIL")
    return 1


def run_command(command: list[str]) -> int:
    if not command:
        print("[FAIL] No command provided. Usage: vw_env.py run -- <cmd...>")
        return 1
    try:
        mapping = load_mapping()
    except RuntimeError as exc:
        print(f"[FAIL] {exc}")
        return 1

    mapping_ok = print_mapping_status(mapping)
    errors = preflight_errors(mapping)
    for err in errors:
        print(f"[FAIL] {err}")
    if not mapping_ok or errors:
        return 1

    injected: dict[str, str] = {}
    for var_name, entry in mapping.items():
        try:
            item = fetch_item(entry["item_id"])
            injected[var_name] = extract_value(item, entry["source"])
            print(f"{var_name}: OK")
        except RuntimeError as exc:
            print(f"{var_name}: MISSING")
            print(f"[FAIL] {exc}")
            return 1

    child_env = os.environ.copy()
    child_env.update(injected)
    completed = subprocess.run(command, check=False, env=child_env)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inject environment variables from Vaultwarden mappings")
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    subparsers.add_parser("check", help="Validate mapping and BW session prerequisites")

    run_parser = subparsers.add_parser("run", help="Run command with injected environment")
    run_parser.add_argument("cmd", nargs=argparse.REMAINDER, help="command after '--'")

    args = parser.parse_args(argv)
    if args.subcommand == "check":
        return run_check()

    cmd = list(args.cmd)
    if cmd and cmd[0] == "--":
        cmd = cmd[1:]
    return run_command(cmd)


if __name__ == "__main__":
    sys.exit(main())
