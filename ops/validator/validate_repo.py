#!/usr/bin/env python3
"""Deterministic repository validator."""

from __future__ import annotations

import pathlib
import subprocess
import sys

REQUIRED_DIRECTORIES = [
    "bootstrap/compose",
    "bootstrap/env",
    "infra/modules",
    "infra/backend",
    "infra/environments/dev",
    "infra/environments/prod",
    "ops/validator",
    "ops/health",
    "ops/backup",
    "ops/audit",
    "policies",
    "skills",
    "scripts",
    "plans",
    "artifacts",
    "docs/decisions",
    "docs/runbooks",
    "n8n/dev",
    "n8n/prod",
]

REQUIRED_FILES = [
    ".gitignore",
    ".editorconfig",
    "Makefile",
    "README.md",
    "docs/inventory.md",
    "docs/CHANGELOG.md",
]

PRIVATE_KEY_MARKERS = [
    b"BEGIN" + b" PRIVATE KEY",
    b"BEGIN" + b" OPENSSH PRIVATE KEY",
]


def git_tracked_files(repo_root: pathlib.Path) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=repo_root,
        capture_output=True,
        text=False,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git ls-files failed: {stderr}")
    raw_items = result.stdout.split(b"\x00")
    files = [item.decode("utf-8", errors="surrogateescape") for item in raw_items if item]
    return sorted(files)


def check_required_directories(repo_root: pathlib.Path) -> list[str]:
    failures: list[str] = []
    for rel_path in REQUIRED_DIRECTORIES:
        target = repo_root / rel_path
        if not target.is_dir():
            failures.append(rel_path)
    return failures


def check_required_files(repo_root: pathlib.Path) -> list[str]:
    failures: list[str] = []
    for rel_path in REQUIRED_FILES:
        target = repo_root / rel_path
        if not target.is_file():
            failures.append(rel_path)
    return failures


def check_gitignore_entries(repo_root: pathlib.Path) -> list[str]:
    gitignore_path = repo_root / ".gitignore"
    if not gitignore_path.is_file():
        return ["plans/", "artifacts/"]

    lines = {
        line.strip()
        for line in gitignore_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }

    missing: list[str] = []
    for entry in ("plans/", "artifacts/"):
        if entry not in lines:
            missing.append(entry)
    return missing


def check_private_keys(repo_root: pathlib.Path, tracked_files: list[str]) -> list[str]:
    flagged: list[str] = []
    for rel_path in tracked_files:
        file_path = repo_root / rel_path
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_bytes()
        except OSError:
            continue
        if any(marker in content for marker in PRIVATE_KEY_MARKERS):
            flagged.append(rel_path)
    return sorted(flagged)


def print_list(items: list[str]) -> None:
    for item in items:
        print(f"  - {item}")


def main() -> int:
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    failures = False

    try:
        tracked_files = git_tracked_files(repo_root)
    except RuntimeError as exc:
        print(f"[FAIL] Could not inspect tracked files: {exc}")
        return 1

    missing_dirs = check_required_directories(repo_root)
    if missing_dirs:
        failures = True
        print("[FAIL] Required directories are missing:")
        print_list(missing_dirs)
    else:
        print("[PASS] Required directories exist.")

    missing_files = check_required_files(repo_root)
    if missing_files:
        failures = True
        print("[FAIL] Required files are missing:")
        print_list(missing_files)
    else:
        print("[PASS] Required files exist.")

    if ".env" in tracked_files:
        failures = True
        print("[FAIL] .env is tracked by git. Remove it from version control.")
    else:
        print("[PASS] .env is not tracked by git.")

    missing_gitignore_entries = check_gitignore_entries(repo_root)
    if missing_gitignore_entries:
        failures = True
        print("[FAIL] .gitignore is missing required entries:")
        print_list(missing_gitignore_entries)
    else:
        print("[PASS] .gitignore contains plans/ and artifacts/.")

    private_key_hits = check_private_keys(repo_root, tracked_files)
    if private_key_hits:
        failures = True
        print("[FAIL] Private key markers found in tracked files:")
        print_list(private_key_hits)
    else:
        print("[PASS] No private key markers found in tracked files.")

    if failures:
        print("Validation failed.")
        return 1

    print("Validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
