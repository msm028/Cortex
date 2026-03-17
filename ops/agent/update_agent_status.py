#!/usr/bin/env python3
"""Build a queue-aware status artifact for the unattended agent loop."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
from pathlib import Path
from typing import Any


DEFAULT_STATUS = "pending"
TASK_STATUSES = {
    "pending",
    "in_progress",
    "completed",
    "blocked-needs-approval",
    "blocked-needs-human-decision",
    "retry-later",
}
RESULT_CLASSES = {
    "retry-scheduled-startup-timeout": "startup-timeout",
    "max-attempts-reached-startup-timeout": "startup-timeout",
    "retry-scheduled-timeout": "timeout",
    "max-attempts-reached-timeout": "timeout",
    "recovered-from-stale-in-progress": "stale-recovery",
    "manual-success": "manual-intervention",
}


def repo_root() -> Path:
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
        check=True,
    )
    return Path(result.stdout.strip())


def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def load_json(path: Path, default: Any) -> Any:
    if not path.is_file():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def queue_dir(root: Path) -> Path:
    return root / "ops" / "queue"


def task_state_path(root: Path) -> Path:
    return root / "artifacts" / "agent" / "task-state.json"


def loop_state_path(root: Path) -> Path:
    return root / "artifacts" / "agent" / "loop-state.json"


def approvals_path(root: Path) -> Path:
    return root / "artifacts" / "agent" / "approvals.json"


def status_path(root: Path) -> Path:
    return root / "artifacts" / "agent" / "agent-status.json"


def _normalize_task(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    task_id = str(payload.get("id") or path.stem)
    actions = payload.get("actions")
    if not isinstance(actions, list):
        actions = []
    return {
        "id": task_id,
        "title": str(payload.get("title") or task_id),
        "summary": str(payload.get("summary") or ""),
        "priority": int(payload.get("priority", 100)),
        "approval_required": bool(payload.get("approval_required", False)),
        "max_attempts": int(payload.get("max_attempts", 3)),
        "retry_delay_seconds": int(payload.get("retry_delay_seconds", 1800)),
        "model_hint": str(payload.get("model_hint") or "low"),
        "path": str(path),
        "relative_path": str(path.relative_to(path.parents[2])),
        "actions": actions,
    }


def load_task_definitions(root: Path) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for path in sorted(queue_dir(root).glob("*.json")):
        payload = load_json(path, None)
        if not isinstance(payload, dict):
            continue
        tasks.append(_normalize_task(path, payload))
    return sorted(tasks, key=lambda item: (item["priority"], item["id"]))


def load_task_state(root: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(task_state_path(root), {})
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for task_id, value in payload.items():
        if isinstance(task_id, str) and isinstance(value, dict):
            result[task_id] = value
    return result


def load_loop_state(root: Path) -> dict[str, Any]:
    payload = load_json(loop_state_path(root), {})
    if not isinstance(payload, dict):
        return {}
    return payload


def load_approvals(root: Path) -> dict[str, dict[str, Any]]:
    payload = load_json(approvals_path(root), {})
    if not isinstance(payload, dict):
        return {}
    result: dict[str, dict[str, Any]] = {}
    for task_id, value in payload.items():
        if isinstance(task_id, str) and isinstance(value, dict):
            result[task_id] = value
    return result


def normalize_status(raw: Any) -> str:
    if isinstance(raw, str) and raw in TASK_STATUSES:
        return raw
    return DEFAULT_STATUS


def classify_result(raw: Any) -> str | None:
    if not isinstance(raw, str):
        return None
    return RESULT_CLASSES.get(raw)


def task_view(
    task: dict[str, Any],
    state: dict[str, dict[str, Any]],
    approvals: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    state_entry = state.get(task["id"], {})
    approval_entry = approvals.get(task["id"])
    last_result = state_entry.get("last_result")
    result_class = classify_result(last_result)
    return {
        "id": task["id"],
        "title": task["title"],
        "summary": task["summary"],
        "priority": task["priority"],
        "approval_required": task["approval_required"],
        "approval_granted": isinstance(approval_entry, dict),
        "approved_at": approval_entry.get("approved_at") if isinstance(approval_entry, dict) else None,
        "status": normalize_status(state_entry.get("status")),
        "attempts": int(state_entry.get("attempts", 0)),
        "max_attempts": task["max_attempts"],
        "retry_after": state_entry.get("retry_after"),
        "last_started_at": state_entry.get("last_started_at"),
        "last_finished_at": state_entry.get("last_finished_at"),
        "last_result": last_result,
        "last_result_class": result_class,
        "last_log": state_entry.get("last_log"),
        "model_hint": task["model_hint"],
        "relative_path": task["relative_path"],
    }


def _queue_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {status: 0 for status in sorted(TASK_STATUSES)}
    for task in tasks:
        counts[task["status"]] = counts.get(task["status"], 0) + 1
    return counts


def _overall_state(tasks: list[dict[str, Any]], loop_state: dict[str, Any]) -> str:
    if loop_state.get("current_task_id"):
        return "RUNNING"
    statuses = {task["status"] for task in tasks}
    if "blocked-needs-approval" in statuses:
        return "WAITING_FOR_APPROVAL"
    if "blocked-needs-human-decision" in statuses:
        return "NEEDS_ATTENTION"
    if "retry-later" in statuses:
        return "RETRY_SCHEDULED"
    if "pending" in statuses:
        return "READY"
    if "completed" in statuses:
        return "IDLE"
    return "IDLE"


def _recent_attention_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    attention_statuses = {"retry-later", "blocked-needs-approval", "blocked-needs-human-decision"}
    ranked = [
        task
        for task in tasks
        if task["status"] in attention_statuses or task.get("last_result_class") is not None
    ]
    ranked.sort(
        key=lambda item: (
            0 if item["status"] in attention_statuses else 1,
            item.get("last_finished_at") or "",
            item.get("last_started_at") or "",
            item["id"],
        ),
        reverse=True,
    )
    return ranked[:5]


def _result_class_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts = {label: 0 for label in sorted(set(RESULT_CLASSES.values()))}
    for task in tasks:
        result_class = task.get("last_result_class")
        if result_class:
            counts[result_class] = counts.get(result_class, 0) + 1
    return counts


def build_status_payload(root: Path) -> dict[str, Any]:
    tasks = load_task_definitions(root)
    state = load_task_state(root)
    approvals = load_approvals(root)
    loop_state = load_loop_state(root)
    views = [task_view(task, state, approvals) for task in tasks]
    counts = _queue_counts(views)
    pending = [task for task in views if task["status"] in {"pending", "retry-later"}]
    blocked = [task for task in views if task["status"] == "blocked-needs-approval"]
    attention = _recent_attention_tasks(views)
    current_task_id = loop_state.get("current_task_id")
    current_task = next((task for task in views if task["id"] == current_task_id), None)
    payload = {
        "generated_at": now_utc().isoformat(),
        "overall_state": _overall_state(views, loop_state),
        "queue_counts": counts,
        "result_class_counts": _result_class_counts(views),
        "current_task": current_task,
        "next_tasks": pending[:5],
        "approval_queue": blocked[:5],
        "attention_tasks": attention,
        "recent_events": list(loop_state.get("recent_events", []))[:10],
        "last_cycle_at": loop_state.get("last_cycle_at"),
        "last_cycle_result": loop_state.get("last_cycle_result"),
        "tasks": views,
    }
    return payload


def write_status(root: Path) -> Path:
    payload = build_status_payload(root)
    out_path = status_path(root)
    write_json(out_path, payload)
    return out_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Update unattended agent status artifact")
    parser.add_argument("--output", help="Optional output path override")
    args = parser.parse_args()

    root = repo_root()
    out_path = Path(args.output).expanduser() if args.output else status_path(root)
    if not out_path.is_absolute():
        out_path = root / out_path
    write_json(out_path, build_status_payload(root))
    print(out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
