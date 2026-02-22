#!/usr/bin/env python3
"""Flywheel runner: validate, optional execute, then update docs."""

from __future__ import annotations

import argparse
import json
import shlex
import subprocess
import sys
from pathlib import Path


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def newest_plan(root: Path) -> Path:
    plans = sorted((root / "plans").glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not plans:
        raise FileNotFoundError("No plan files found under plans/*.json")
    return plans[0]


def validate_plan_file(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"Plan file not found: {path}")
    try:
        json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"Plan is not valid JSON: {path} ({exc})") from exc


def run_cmd(argv: list[str], cwd: Path) -> None:
    subprocess.run(argv, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run flywheel workflow")
    parser.add_argument("--message", required=True, help="Changelog message")
    parser.add_argument("--plan", help="Plan path (defaults to newest plans/*.json)")
    parser.add_argument("--exec", dest="exec_cmd", help="Command template; use {plan} placeholder")
    parser.add_argument("--yes", action="store_true", help="Required to execute --exec command")
    parser.add_argument("--no-validate", action="store_true", help="Skip make validate")
    args = parser.parse_args()

    root = repo_root()
    plan_path = Path(args.plan).expanduser() if args.plan else newest_plan(root)
    if not plan_path.is_absolute():
        plan_path = root / plan_path
    validate_plan_file(plan_path)

    if not args.no_validate:
        run_cmd(["make", "validate"], root)

    if args.exec_cmd:
        final = args.exec_cmd.replace("{plan}", str(plan_path))
        print(f"[INFO] exec command: {final}")
        if not args.yes:
            print("[SAFE-EXIT] --exec provided without --yes; command not executed.")
            return 1
        run_cmd(shlex.split(final), root)

    doc_message = f"{args.message} (plan: {plan_path.name})"
    update_cmd = ["python3", "skills/update-docs/update-docs.py", "--message", doc_message]
    if args.no_validate:
        update_cmd.append("--no-validate")
    run_cmd(update_cmd, root)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (FileNotFoundError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"[FAIL] {exc}")
        raise SystemExit(1) from exc
