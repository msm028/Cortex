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


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a deterministic execution plan")
    parser.add_argument(
        "--name-prefix",
        default="plan",
        help="Filename prefix for the generated plan (default: plan)",
    )
    args = parser.parse_args()

    timestamp = dt.datetime.now(dt.timezone.utc)
    ts_compact = timestamp.strftime("%Y%m%dT%H%M%SZ")
    created_at = timestamp.replace(microsecond=0).isoformat().replace("+00:00", "Z")

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
