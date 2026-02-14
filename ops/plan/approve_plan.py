#!/usr/bin/env python3
"""Write approval files bound to canonical plan hash."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def canonical_json_bytes(data: object) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def normalize_plan_path(plan_arg: str) -> Path:
    path = Path(plan_arg)
    if not path.is_absolute():
        path = REPO_ROOT / path
    return path.resolve()


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve a plan by binding approval to plan hash")
    parser.add_argument("--plan", required=True, help="Path to plan JSON file")
    parser.add_argument("--vaultwarden-item-id", required=True, help="Vaultwarden item ID reference")
    args = parser.parse_args()

    plan_path = normalize_plan_path(args.plan)
    if not plan_path.is_file():
        print(f"[FAIL] Plan file not found: {plan_path}")
        return 1

    try:
        plan_data = json.loads(plan_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"[FAIL] Plan file is not valid JSON: {exc}")
        return 1

    digest = hashlib.sha256(canonical_json_bytes(plan_data)).hexdigest()
    approval_path = Path(str(plan_path) + ".approved")
    approval_content = (
        f"vaultwarden_item_id: {args.vaultwarden_item_id}\n"
        f"plan_sha256: {digest}\n"
        f"approved_at: {now_utc()}\n"
    )
    approval_path.write_text(approval_content, encoding="utf-8")

    print(f"[PASS] Approval file written: {approval_path.relative_to(REPO_ROOT)}")
    print(f"[PASS] plan_sha256: {digest}")
    print(f"[PASS] vaultwarden_item_id: {args.vaultwarden_item_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
