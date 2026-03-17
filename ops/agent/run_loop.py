#!/usr/bin/env python3
"""Run a bounded unattended task loop with explicit approval gates."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ops.agent.update_agent_status import (
    build_status_payload,
    load_approvals,
    load_task_definitions,
    load_task_state,
    loop_state_path,
    now_utc,
    repo_root,
    status_path,
    task_state_path,
    write_json,
)


LOGS_DIR_REL = Path("artifacts/agent/runs")
DEFAULT_CODEX_EXEC_TIMEOUT_SECONDS = 900
DEFAULT_TIMEOUT_GRACE_SECONDS = 5
DEFAULT_CODEX_EXEC_HEARTBEAT_SECONDS = 30


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    lowered = re.sub(r"[^a-z0-9]+", "-", lowered)
    return lowered.strip("-") or "task"


def load_loop_state(root: Path) -> dict[str, Any]:
    path = loop_state_path(root)
    if not path.is_file():
        return {"recent_events": []}
    try:
        import json

        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {"recent_events": []}
    if not isinstance(payload, dict):
        return {"recent_events": []}
    payload.setdefault("recent_events", [])
    return payload


def task_effective_status(task_id: str, task_state: dict[str, dict[str, Any]]) -> str:
    entry = task_state.get(task_id, {})
    status = entry.get("status", "pending")
    if not isinstance(status, str):
        return "pending"
    return status


def _is_retry_ready(entry: dict[str, Any], current_time: dt.datetime) -> bool:
    retry_after = entry.get("retry_after")
    if not isinstance(retry_after, str) or not retry_after:
        return True
    try:
        retry_at = dt.datetime.fromisoformat(retry_after)
    except ValueError:
        return True
    if retry_at.tzinfo is None:
        retry_at = retry_at.replace(tzinfo=dt.timezone.utc)
    return retry_at <= current_time


def append_event(loop_state: dict[str, Any], task_id: str, status: str, message: str) -> None:
    event = {
        "timestamp": now_utc().isoformat(),
        "task_id": task_id,
        "status": status,
        "message": message,
    }
    events = list(loop_state.get("recent_events", []))
    if events:
        latest = events[0]
        if (
            isinstance(latest, dict)
            and latest.get("task_id") == task_id
            and latest.get("status") == status
            and latest.get("message") == message
        ):
            return
    loop_state["recent_events"] = [event, *events][:20]


def save_state(root: Path, task_state: dict[str, dict[str, Any]], loop_state: dict[str, Any]) -> None:
    write_json(task_state_path(root), task_state)
    write_json(loop_state_path(root), loop_state)
    write_json(status_path(root), build_status_payload(root))


def set_task_state(
    task_state: dict[str, dict[str, Any]],
    task_id: str,
    **fields: Any,
) -> dict[str, Any]:
    entry = dict(task_state.get(task_id, {}))
    entry.update(fields)
    task_state[task_id] = entry
    return entry


def recover_stale_in_progress_tasks(
    tasks: list[dict[str, Any]],
    task_state: dict[str, dict[str, Any]],
    loop_state: dict[str, Any],
) -> None:
    current_task_id = loop_state.get("current_task_id")
    if current_task_id:
        loop_state["current_task_id"] = None
        loop_state["current_task_title"] = None

    by_id = {task["id"]: task for task in tasks}
    for task_id, entry in list(task_state.items()):
        if task_effective_status(task_id, task_state) != "in_progress":
            continue
        task = by_id.get(task_id)
        if task is None:
            continue
        attempts = int(entry.get("attempts", 0))
        recovered_status = "retry-later"
        recovered_result = "recovered-from-stale-in-progress"
        extra_fields: dict[str, Any] = {"retry_after": now_utc().isoformat()}
        if attempts >= task["max_attempts"]:
            recovered_status = "blocked-needs-human-decision"
            recovered_result = "max-attempts-reached"
            extra_fields = {"retry_after": None}
        set_task_state(
            task_state,
            task_id,
            status=recovered_status,
            last_result=recovered_result,
            last_finished_at=now_utc().isoformat(),
            **extra_fields,
        )
        append_event(loop_state, task_id, recovered_status, recovered_result)


def select_task(
    tasks: list[dict[str, Any]],
    task_state: dict[str, dict[str, Any]],
    approvals: dict[str, dict[str, Any]],
    loop_state: dict[str, Any],
    allow_codex_exec: bool,
) -> dict[str, Any] | None:
    current_time = now_utc()
    for task in tasks:
        if not allow_codex_exec and any(
            isinstance(action, dict) and str(action.get("type") or "shell") == "codex_exec"
            for action in task.get("actions", [])
        ):
            continue
        entry = task_state.get(task["id"], {})
        status = task_effective_status(task["id"], task_state)
        if status == "blocked-needs-approval" and task["id"] in approvals:
            status = "pending"
            set_task_state(
                task_state,
                task["id"],
                status="pending",
                last_result="approval-received",
                last_finished_at=current_time.isoformat(),
            )
            append_event(loop_state, task["id"], "pending", "approval received")
            entry = task_state.get(task["id"], {})
        elif status not in {"pending", "retry-later"}:
            continue
        if status == "retry-later" and not _is_retry_ready(entry, current_time):
            continue
        if task["approval_required"] and task["id"] not in approvals:
            current = task_effective_status(task["id"], task_state)
            if current != "blocked-needs-approval":
                set_task_state(
                    task_state,
                    task["id"],
                    status="blocked-needs-approval",
                    last_result="approval-required",
                    last_finished_at=current_time.isoformat(),
                )
                append_event(loop_state, task["id"], "blocked-needs-approval", "waiting for approval")
            continue
        return task
    return None


def _log_path(root: Path, task: dict[str, Any]) -> Path:
    stamp = now_utc().strftime("%Y%m%dT%H%M%SZ")
    return root / LOGS_DIR_REL / f"{stamp}-{slugify(task['id'])}.log"


def resolve_model_name(model_hint: str | None) -> str | None:
    if model_hint == "low":
        value = os.environ.get("CODEX_LOW_MODEL", "").strip()
        return value or None
    if model_hint == "high":
        value = os.environ.get("CODEX_HIGH_MODEL", "").strip()
        return value or None
    value = os.environ.get("CODEX_DEFAULT_MODEL", "").strip()
    return value or None


def resolve_codex_bin() -> str | None:
    env_value = os.environ.get("CODEX_BIN", "").strip()
    if env_value:
        path = Path(env_value).expanduser()
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)

    discovered = shutil.which("codex")
    if discovered:
        return discovered

    home = Path.home()
    candidates = [home / ".local" / "bin" / "codex"]
    candidates.extend(sorted((home / ".nvm" / "versions" / "node").glob("*/bin/codex"), reverse=True))
    for path in candidates:
        if path.is_file() and os.access(path, os.X_OK):
            return str(path)
    return None


def resolve_codex_command() -> list[str] | None:
    codex_bin = resolve_codex_bin()
    if codex_bin is None:
        return None
    raw_path = Path(codex_bin).expanduser()
    codex_path = raw_path.resolve()
    node_path = raw_path.parent / "node"
    if node_path.is_file() and os.access(node_path, os.X_OK):
        return [str(node_path), str(codex_path)]
    return [str(codex_path)]


def build_action_invocation(
    task: dict[str, Any],
    action: dict[str, Any],
    root: Path,
    action_index: int,
    log_path: Path,
) -> tuple[list[str] | None, str, Path | None, int | None, int | None, str | None]:
    action_type = str(action.get("type") or "shell")
    cwd = str(action.get("cwd") or ".")
    run_cwd = root / cwd
    timeout_value = action.get("timeout_seconds")
    timeout_seconds: int | None = None
    if timeout_value is not None:
        if not isinstance(timeout_value, int) or timeout_value <= 0:
            return None, cwd, None, None, None, "invalid timeout_seconds"
        timeout_seconds = timeout_value
    heartbeat_value = action.get("heartbeat_seconds")
    heartbeat_seconds: int | None = None
    if heartbeat_value is not None:
        if not isinstance(heartbeat_value, int) or heartbeat_value <= 0:
            return None, cwd, None, None, None, "invalid heartbeat_seconds"
        heartbeat_seconds = heartbeat_value

    if action_type == "shell":
        argv = action.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) for item in argv):
            return None, cwd, None, None, None, "invalid argv"
        env_timeout = os.environ.get("AGENT_ACTION_TIMEOUT_SECONDS", "").strip()
        if timeout_seconds is None and env_timeout:
            try:
                timeout_seconds = int(env_timeout)
            except ValueError:
                return None, cwd, None, None, None, "invalid AGENT_ACTION_TIMEOUT_SECONDS"
            if timeout_seconds <= 0:
                return None, cwd, None, None, None, "invalid AGENT_ACTION_TIMEOUT_SECONDS"
        env_heartbeat = os.environ.get("AGENT_ACTION_HEARTBEAT_SECONDS", "").strip()
        if heartbeat_seconds is None and env_heartbeat:
            try:
                heartbeat_seconds = int(env_heartbeat)
            except ValueError:
                return None, cwd, None, None, None, "invalid AGENT_ACTION_HEARTBEAT_SECONDS"
            if heartbeat_seconds <= 0:
                return None, cwd, None, None, None, "invalid AGENT_ACTION_HEARTBEAT_SECONDS"
        return argv, cwd, None, timeout_seconds, heartbeat_seconds, None

    if action_type == "codex_exec":
        prompt = action.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            return None, cwd, None, None, None, "invalid prompt"
        codex_command = resolve_codex_command()
        if codex_command is None:
            return None, cwd, None, None, None, "codex executable not found"
        sandbox = str(action.get("sandbox") or "workspace-write")
        profile = action.get("profile")
        model_hint = str(action.get("model_hint") or task.get("model_hint") or "low")
        message_path = log_path.with_name(f"{log_path.stem}.action{action_index}.last-message.txt")
        argv = [*codex_command, "exec", "--color", "never", "--sandbox", sandbox, "--full-auto", "-o", str(message_path)]
        if action.get("ephemeral"):
            argv.append("--ephemeral")
        if isinstance(profile, str) and profile.strip():
            argv.extend(["-p", profile.strip()])
        explicit_model = action.get("model")
        model_name = explicit_model.strip() if isinstance(explicit_model, str) and explicit_model.strip() else resolve_model_name(model_hint)
        if model_name:
            argv.extend(["-m", model_name])
        argv.append(prompt)
        if not run_cwd.is_dir():
            return None, cwd, None, None, None, "invalid cwd"
        if timeout_seconds is None:
            env_timeout = os.environ.get("CODEX_EXEC_TIMEOUT_SECONDS", "").strip()
            if env_timeout:
                try:
                    timeout_seconds = int(env_timeout)
                except ValueError:
                    return None, cwd, None, None, None, "invalid CODEX_EXEC_TIMEOUT_SECONDS"
                if timeout_seconds <= 0:
                    return None, cwd, None, None, None, "invalid CODEX_EXEC_TIMEOUT_SECONDS"
            else:
                timeout_seconds = DEFAULT_CODEX_EXEC_TIMEOUT_SECONDS
        if heartbeat_seconds is None:
            env_heartbeat = os.environ.get("CODEX_EXEC_HEARTBEAT_SECONDS", "").strip()
            if env_heartbeat:
                try:
                    heartbeat_seconds = int(env_heartbeat)
                except ValueError:
                    return None, cwd, None, None, None, "invalid CODEX_EXEC_HEARTBEAT_SECONDS"
                if heartbeat_seconds <= 0:
                    return None, cwd, None, None, None, "invalid CODEX_EXEC_HEARTBEAT_SECONDS"
            else:
                heartbeat_seconds = DEFAULT_CODEX_EXEC_HEARTBEAT_SECONDS
        return argv, cwd, message_path, timeout_seconds, heartbeat_seconds, None

    return None, cwd, None, None, None, f"unsupported action type: {action_type}"


def _terminate_process_group(process: subprocess.Popen[str], grace_seconds: int) -> None:
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    except OSError:
        process.terminate()
    try:
        process.wait(timeout=grace_seconds)
        return
    except subprocess.TimeoutExpired:
        pass
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    except OSError:
        process.kill()
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        pass


def run_action(
    argv: list[str],
    *,
    cwd: Path,
    timeout_seconds: int | None,
    heartbeat_seconds: int | None,
    heartbeat_callback: Callable[[int], None] | None = None,
) -> tuple[int, str, str, bool]:
    process = subprocess.Popen(
        argv,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    timed_out = False
    stdout = ""
    stderr = ""
    if timeout_seconds is None and heartbeat_seconds is None:
        stdout, stderr = process.communicate()
        return process.returncode or 0, stdout, stderr, timed_out

    started_at = time.monotonic()
    deadline = started_at + timeout_seconds if timeout_seconds is not None else None
    next_heartbeat = started_at + heartbeat_seconds if heartbeat_seconds is not None else None
    while True:
        try:
            now = time.monotonic()
            wait_timeout: float | None = None
            if deadline is not None:
                remaining = deadline - now
                if remaining <= 0:
                    raise subprocess.TimeoutExpired(cmd=argv, timeout=timeout_seconds, output=stdout, stderr=stderr)
                wait_timeout = remaining
            if next_heartbeat is not None:
                heartbeat_wait = next_heartbeat - now
                if heartbeat_wait <= 0:
                    if heartbeat_callback is not None:
                        heartbeat_callback(int(max(1, now - started_at)))
                    next_heartbeat += heartbeat_seconds or 0
                    continue
                wait_timeout = heartbeat_wait if wait_timeout is None else min(wait_timeout, heartbeat_wait)
            stdout, stderr = process.communicate(timeout=wait_timeout)
            break
        except subprocess.TimeoutExpired:
            now = time.monotonic()
            if deadline is not None and now >= deadline:
                timed_out = True
                _terminate_process_group(process, DEFAULT_TIMEOUT_GRACE_SECONDS)
                remaining_stdout, remaining_stderr = process.communicate()
                stdout += remaining_stdout or ""
                stderr += remaining_stderr or ""
                timeout_note = f"\n[TIMEOUT] action exceeded {timeout_seconds} second(s) and was terminated.\n"
                stderr = f"{stderr}{timeout_note}" if stderr else timeout_note
                break
            if heartbeat_callback is not None:
                heartbeat_callback(int(max(1, now - started_at)))
            next_heartbeat = now + (heartbeat_seconds or 0)
    return process.returncode or 0, stdout, stderr, timed_out


def run_task(root: Path, task: dict[str, Any], task_state: dict[str, dict[str, Any]], loop_state: dict[str, Any]) -> str:
    current_time = now_utc()
    entry = task_state.get(task["id"], {})
    attempts = int(entry.get("attempts", 0)) + 1
    log_path = _log_path(root, task)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    set_task_state(
        task_state,
        task["id"],
        status="in_progress",
        attempts=attempts,
        last_started_at=current_time.isoformat(),
        last_log=str(log_path.relative_to(root)),
        retry_after=None,
    )
    loop_state["current_task_id"] = task["id"]
    loop_state["current_task_title"] = task["title"]
    append_event(loop_state, task["id"], "in_progress", "task started")
    save_state(root, task_state, loop_state)

    success = True
    failure_reason = "action-failed"
    with log_path.open("w", encoding="utf-8") as handle:
        handle.write(f"TASK {task['id']}\n")
        handle.write(f"TITLE {task['title']}\n")
        handle.write(f"MODEL_HINT {task['model_hint']}\n")
        for index, action in enumerate(task.get("actions", []), start=1):
            argv, cwd, message_path, timeout_seconds, heartbeat_seconds, error = build_action_invocation(task, action, root, index, log_path)
            if error or argv is None:
                success = False
                failure_reason = "invalid-action"
                handle.write(f"[ACTION-{index}] {error or 'invalid action'}\n")
                break
            run_cwd = root / cwd
            handle.write(f"[ACTION-{index}] type={action.get('type', 'shell')}\n")
            handle.write(f"[ACTION-{index}] cwd={cwd}\n")
            handle.write(f"[ACTION-{index}] argv={' '.join(argv)}\n")
            if timeout_seconds is not None:
                handle.write(f"[ACTION-{index}] timeout_seconds={timeout_seconds}\n")
            if heartbeat_seconds is not None:
                handle.write(f"[ACTION-{index}] heartbeat_seconds={heartbeat_seconds}\n")
            handle.flush()
            heartbeat_prefix = f"[ACTION-{index}]"
            heartbeat_count = 0
            def _heartbeat(elapsed_seconds: int) -> None:
                nonlocal heartbeat_count
                heartbeat_count += 1
                handle.write(f"{heartbeat_prefix} [HEARTBEAT] still running after {elapsed_seconds} second(s)\n")
                handle.flush()
            returncode, stdout, stderr, timed_out = run_action(
                argv,
                cwd=run_cwd,
                timeout_seconds=timeout_seconds,
                heartbeat_seconds=heartbeat_seconds,
                heartbeat_callback=_heartbeat,
            )
            handle.write(f"[ACTION-{index}] exit={returncode}\n")
            handle.write("[STDOUT]\n")
            handle.write(stdout)
            if stdout and not stdout.endswith("\n"):
                handle.write("\n")
            handle.write("[STDERR]\n")
            handle.write(stderr)
            if stderr and not stderr.endswith("\n"):
                handle.write("\n")
            last_message = ""
            if message_path and message_path.is_file():
                last_message = message_path.read_text(encoding="utf-8", errors="replace")
                handle.write("[LAST_MESSAGE]\n")
                handle.write(last_message)
                if not last_message.endswith("\n"):
                    handle.write("\n")
            if timed_out:
                success = False
                has_visible_progress = bool(stdout.strip()) or bool(last_message.strip()) or heartbeat_count > 0
                if has_visible_progress:
                    failure_reason = "action-timeout"
                else:
                    failure_reason = "action-startup-timeout"
                    handle.write(f"{heartbeat_prefix} [STARTUP_TIMEOUT] no output, heartbeat, or last message was captured before timeout\n")
                break
            if returncode != 0:
                success = False
                failure_reason = "action-failed"
                break

    finished = now_utc()
    loop_state["current_task_id"] = None
    loop_state["current_task_title"] = None

    if success:
        set_task_state(
            task_state,
            task["id"],
            status="completed",
            last_result="success",
            last_finished_at=finished.isoformat(),
        )
        append_event(loop_state, task["id"], "completed", "task completed")
        return "completed"

    next_status = "retry-later"
    timeout_results = {
        "action-timeout": "retry-scheduled-timeout",
        "action-startup-timeout": "retry-scheduled-startup-timeout",
    }
    next_result = timeout_results.get(failure_reason, "retry-scheduled")
    extra_fields: dict[str, Any] = {}
    if attempts >= task["max_attempts"]:
        next_status = "blocked-needs-human-decision"
        timeout_block_results = {
            "action-timeout": "max-attempts-reached-timeout",
            "action-startup-timeout": "max-attempts-reached-startup-timeout",
        }
        next_result = timeout_block_results.get(failure_reason, "max-attempts-reached")
    else:
        retry_at = finished + dt.timedelta(seconds=task["retry_delay_seconds"])
        extra_fields["retry_after"] = retry_at.isoformat()
    set_task_state(
        task_state,
        task["id"],
        status=next_status,
        last_result=next_result,
        last_finished_at=finished.isoformat(),
        **extra_fields,
    )
    append_event(loop_state, task["id"], next_status, next_result)
    return next_status


def run_cycle(root: Path, max_tasks: int, allow_codex_exec: bool) -> str:
    tasks = load_task_definitions(root)
    task_state = load_task_state(root)
    approvals = load_approvals(root)
    loop_state = load_loop_state(root)
    recover_stale_in_progress_tasks(tasks, task_state, loop_state)
    loop_state["last_cycle_at"] = now_utc().isoformat()
    completed_work = 0
    result = "idle"

    while completed_work < max_tasks:
        task = select_task(tasks, task_state, approvals, loop_state, allow_codex_exec=allow_codex_exec)
        if task is None:
            break
        result = run_task(root, task, task_state, loop_state)
        completed_work += 1

    if completed_work == 0:
        result = result if result != "idle" else "idle"
    loop_state["last_cycle_result"] = result
    save_state(root, task_state, loop_state)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the unattended Cortex task loop")
    parser.add_argument("--run-once", action="store_true", help="Process at most one cycle and exit")
    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=600,
        help="Sleep interval between cycles when not using --run-once",
    )
    parser.add_argument(
        "--max-tasks-per-cycle",
        type=int,
        default=1,
        help="Maximum tasks to execute per cycle",
    )
    parser.add_argument(
        "--allow-codex-exec",
        action="store_true",
        help="Allow queued codex_exec actions to run in this loop process",
    )
    args = parser.parse_args()

    root = repo_root()
    if args.run_once:
        print(run_cycle(root, max_tasks=args.max_tasks_per_cycle, allow_codex_exec=args.allow_codex_exec))
        return 0

    while True:
        result = run_cycle(root, max_tasks=args.max_tasks_per_cycle, allow_codex_exec=args.allow_codex_exec)
        print(result, flush=True)
        time.sleep(max(1, args.sleep_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
