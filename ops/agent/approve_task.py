#!/usr/bin/env python3
"""Write approval records for queued unattended agent tasks."""

from __future__ import annotations

import argparse
import datetime as dt
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.agent.update_agent_status import approvals_path, load_approvals, repo_root, write_json


def main() -> int:
    parser = argparse.ArgumentParser(description="Approve a queued unattended agent task")
    parser.add_argument("--task", required=True, help="Task ID to approve")
    parser.add_argument("--note", default="", help="Optional approval note")
    args = parser.parse_args()

    root = repo_root()
    approvals = load_approvals(root)
    approvals[args.task] = {
        "approved_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "note": args.note,
    }
    write_json(approvals_path(root), approvals)
    print(f"AGENT-APPROVAL: OK {args.task}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
