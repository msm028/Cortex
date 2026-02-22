#!/usr/bin/env python3
"""Inspect and risk-summarise plan JSON files."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path
from typing import Any


COUNT_KEYS = ("steps", "actions", "operations", "tasks", "resources", "changes", "items")
TARGET_KEYS = ("host", "hostname", "ip", "address", "node", "target")


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def list_plan_files(root: Path) -> list[Path]:
    plans_dir = root / "plans"
    return sorted(plans_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def parse_plan(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def local_mtime(path: Path) -> str:
    return dt.datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def parse_infra_examples(config_path: Path) -> list[str]:
    if not config_path.is_file():
        return []
    text = config_path.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"infra_step_examples\s*=\s*\[(.*?)\]", text, flags=re.DOTALL)
    if not match:
        return []
    inner = match.group(1)
    return [m.group(1) for m in re.finditer(r'"([^"]+)"', inner)]


def iter_json(node: Any, path: str = "$"):
    yield path, node
    if isinstance(node, dict):
        for key, value in node.items():
            yield from iter_json(value, f"{path}.{key}")
    elif isinstance(node, list):
        for i, value in enumerate(node):
            yield from iter_json(value, f"{path}[{i}]")


def find_infra_matches(plan: Any, indicators: list[str], limit: int = 12) -> list[dict[str, str]]:
    results: list[dict[str, str]] = []
    lower_indicators = [(item, item.lower()) for item in indicators if item.strip()]
    if not lower_indicators:
        return results
    for path, value in iter_json(plan):
        if isinstance(value, str):
            lowered = value.lower()
            for raw, needle in lower_indicators:
                if needle in lowered:
                    results.append(
                        {"indicator": raw, "path": path, "sample": value[:120].replace("\n", " ")}
                    )
                    if len(results) >= limit:
                        return results
    return results


def find_targets(plan: Any, limit: int = 12) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for path, node in iter_json(plan):
        if not isinstance(node, dict):
            continue
        for key, value in node.items():
            if key.lower() in TARGET_KEYS and isinstance(value, (str, int, float, bool)):
                out.append({"key": key, "path": f"{path}.{key}", "value": str(value)})
                if len(out) >= limit:
                    return out
    return out


def count_common_keys(plan: Any) -> dict[str, int | None]:
    counts: dict[str, int | None] = {}
    if not isinstance(plan, dict):
        for key in COUNT_KEYS:
            counts[key] = None
        return counts
    for key in COUNT_KEYS:
        value = plan.get(key)
        if isinstance(value, (list, dict)):
            counts[key] = len(value)
        else:
            counts[key] = None
    return counts


def build_summary(plan_path: Path, plan: Any, indicators: list[str]) -> dict[str, Any]:
    top_keys = sorted(plan.keys()) if isinstance(plan, dict) else []
    return {
        "plan_filename": plan_path.name,
        "plan_path": str(plan_path.resolve()),
        "mtime_local": local_mtime(plan_path),
        "size_bytes": plan_path.stat().st_size,
        "top_level_keys": top_keys,
        "counts": count_common_keys(plan),
        "infra_indicator_count": len(indicators),
        "infra_matches": find_infra_matches(plan, indicators),
        "targets": find_targets(plan),
    }


def print_human_summary(summary: dict[str, Any]) -> None:
    print(f"plan: {summary['plan_filename']}")
    print(f"path: {summary['plan_path']}")
    print(f"mtime_local: {summary['mtime_local']}")
    print(f"size_bytes: {summary['size_bytes']}")
    print("top_level_keys:", ", ".join(summary["top_level_keys"]) if summary["top_level_keys"] else "<none>")
    print("counts:")
    for key, value in summary["counts"].items():
        rendered = str(value) if value is not None else "-"
        print(f"  - {key}: {rendered}")
    print(f"infra_indicators_loaded: {summary['infra_indicator_count']}")
    print("infra_matches:")
    if summary["infra_matches"]:
        for item in summary["infra_matches"]:
            print(f"  - indicator={item['indicator']} path={item['path']} sample={item['sample']}")
    else:
        print("  - <none>")
    print("targets:")
    if summary["targets"]:
        for item in summary["targets"]:
            print(f"  - key={item['key']} path={item['path']} value={item['value']}")
    else:
        print("  - <none>")


def list_recent(plans: list[Path], count: int) -> int:
    if not plans:
        print("No plan files found under plans/*.json")
        return 0
    print(f"Recent plans (count={min(count, len(plans))}):")
    for plan in plans[:count]:
        print(f"- {plan} | mtime_local={local_mtime(plan)} | size={plan.stat().st_size}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect and risk-summarise plan files")
    parser.add_argument("--list", nargs="?", const="10", help="List most recent plans (default 10)")
    parser.add_argument("--plan", default="latest", help='Plan path to inspect, or "latest"')
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    root = repo_root()
    plans = list_plan_files(root)

    if args.list is not None:
        try:
            count = int(args.list)
        except ValueError:
            print(f"[FAIL] --list must be an integer, got: {args.list}")
            return 1
        return list_recent(plans, max(0, count))

    if args.plan == "latest":
        if not plans:
            print("[FAIL] No plan files found under plans/*.json")
            return 1
        plan_path = plans[0]
    else:
        candidate = Path(args.plan).expanduser()
        plan_path = candidate if candidate.is_absolute() else (root / candidate)
        if not plan_path.is_file():
            print(f"[FAIL] Plan file not found: {plan_path}")
            return 1

    try:
        plan = parse_plan(plan_path)
    except json.JSONDecodeError as exc:
        print(f"[FAIL] Plan is not valid JSON: {plan_path} ({exc})")
        return 1

    indicators = parse_infra_examples(root / ".codex" / "config.toml")
    summary = build_summary(plan_path, plan, indicators)
    if args.json:
        print(json.dumps(summary, indent=2, sort_keys=True))
    else:
        print_human_summary(summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
