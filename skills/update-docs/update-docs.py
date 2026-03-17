#!/usr/bin/env python3
"""Script-first docs updater for changelog and inventory metadata."""

from __future__ import annotations

import argparse
import datetime as dt
import subprocess
from pathlib import Path


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


def ensure_changelog(path: Path) -> list[str]:
    if not path.exists():
        return ["# Changelog", "", "## Unreleased", ""]
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines:
        return ["# Changelog", "", "## Unreleased", ""]
    if lines[0].strip() != "# Changelog":
        lines.insert(0, "# Changelog")
        lines.insert(1, "")
    if "## Unreleased" not in lines:
        insert_at = 2 if len(lines) >= 2 else len(lines)
        lines.insert(insert_at, "## Unreleased")
        lines.insert(insert_at + 1, "")
    return lines


def add_unreleased_bullet(lines: list[str], bullet: str) -> list[str]:
    if bullet in lines:
        return lines
    try:
        idx = lines.index("## Unreleased")
    except ValueError:
        lines.extend(["## Unreleased", "", bullet])
        return lines
    insert_at = idx + 1
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        insert_at += 1
    lines.insert(insert_at, bullet)
    return lines


def ensure_inventory(path: Path, stamp: str) -> list[str]:
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    else:
        lines = ["# Inventory", ""]
    if not lines:
        lines = ["# Inventory", ""]

    updated_line = f"Last updated: {stamp} (local)"
    replaced = False
    for i, line in enumerate(lines):
        if line.startswith("Last updated:"):
            lines[i] = updated_line
            replaced = True
            break
    if replaced:
        return lines

    h1_index = next((i for i, line in enumerate(lines) if line.startswith("# ")), 0)
    insert_at = h1_index + 1
    if insert_at < len(lines) and lines[insert_at].strip() == "":
        lines.insert(insert_at + 1, updated_line)
    else:
        lines.insert(insert_at, "")
        lines.insert(insert_at + 1, updated_line)
    return lines


def write_lines(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines).rstrip() + "\n"
    path.write_text(content, encoding="utf-8")


def run_make(repo: Path, target: str) -> None:
    subprocess.run(["make", target], cwd=repo, check=True)


def run_script(repo: Path, script: list[str]) -> None:
    subprocess.run(script, cwd=repo, check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Update docs changelog and inventory timestamp")
    parser.add_argument("--message", required=True, help="Unreleased changelog message")
    parser.add_argument("--no-validate", action="store_true", help="Skip docs validation make targets")
    args = parser.parse_args()

    root = repo_root()
    docs_dir = root / "docs"
    changelog = docs_dir / "CHANGELOG.md"
    inventory = docs_dir / "inventory.md"

    stamp = now_local_stamp()
    bullet = f"- {stamp} (local): {args.message}"

    changelog_lines = ensure_changelog(changelog)
    changelog_lines = add_unreleased_bullet(changelog_lines, bullet)
    write_lines(changelog, changelog_lines)

    inventory_lines = ensure_inventory(inventory, stamp)
    write_lines(inventory, inventory_lines)

    run_script(root, ["python3", "ops/bin/project_manifest.py", "catalog", "--output", "docs/projects.md"])
    run_script(root, ["python3", "ops/agent/update_agent_status.py"])
    run_script(root, ["python3", "skills/ops-status/update-ops-status.py"])

    if not args.no_validate:
        run_make(root, "docs-build")
        run_make(root, "validate-codex-config")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
