#!/usr/bin/env python3
"""Unit tests for the unattended Cortex agent loop."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_module(module_path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"failed to load module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class AgentLoopTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "ops" / "queue").mkdir(parents=True)
        (self.root / "artifacts" / "agent").mkdir(parents=True)
        self.status_module = load_module(
            REPO_ROOT / "ops" / "agent" / "update_agent_status.py",
            "update_agent_status_for_tests",
        )
        with mock.patch("subprocess.run") as run_mock:
            run_mock.return_value.stdout = str(self.root)
            run_mock.return_value.returncode = 0
            self.loop_module = load_module(
                REPO_ROOT / "ops" / "agent" / "run_loop.py",
                "run_loop_for_tests",
            )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_task(self, name: str, payload: dict) -> None:
        (self.root / "ops" / "queue" / name).write_text(
            json.dumps(payload, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_run_once_completes_non_approval_task(self) -> None:
        self._write_task(
            "100-test.json",
            {
                "id": "test-task",
                "title": "Run echo",
                "priority": 100,
                "actions": [{"argv": ["python3", "-c", "print('ok')"], "cwd": "."}],
            },
        )

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch("sys.argv", ["run_loop.py", "--run-once"]):
                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        task_state = json.loads((self.root / "artifacts" / "agent" / "task-state.json").read_text(encoding="utf-8"))
        self.assertEqual(task_state["test-task"]["status"], "completed")
        self.assertTrue((self.root / "artifacts" / "agent" / "agent-status.json").is_file())

    def test_approval_required_task_blocks_then_can_run_after_approval(self) -> None:
        self._write_task(
            "100-approval.json",
            {
                "id": "approval-task",
                "title": "Wait for approval",
                "priority": 100,
                "approval_required": True,
                "actions": [{"argv": ["python3", "-c", "print('approved')"], "cwd": "."}],
            },
        )
        self._write_task(
            "110-auto.json",
            {
                "id": "auto-task",
                "title": "Automatic task",
                "priority": 110,
                "actions": [{"argv": ["python3", "-c", "print('auto')"], "cwd": "."}],
            },
        )

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch("sys.argv", ["run_loop.py", "--run-once", "--max-tasks-per-cycle", "2"]):
                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        task_state = json.loads((self.root / "artifacts" / "agent" / "task-state.json").read_text(encoding="utf-8"))
        self.assertEqual(task_state["approval-task"]["status"], "blocked-needs-approval")
        self.assertEqual(task_state["auto-task"]["status"], "completed")

        approvals = {
            "approval-task": {"approved_at": "2026-03-16T00:00:00+00:00", "note": "ok"}
        }
        (self.root / "artifacts" / "agent" / "approvals.json").write_text(
            json.dumps(approvals, indent=2) + "\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch("sys.argv", ["run_loop.py", "--run-once"]):
                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        task_state = json.loads((self.root / "artifacts" / "agent" / "task-state.json").read_text(encoding="utf-8"))
        self.assertEqual(task_state["approval-task"]["status"], "completed")

    def test_failure_retries_then_blocks_for_human(self) -> None:
        self._write_task(
            "100-fail.json",
            {
                "id": "fail-task",
                "title": "Failing task",
                "priority": 100,
                "max_attempts": 1,
                "actions": [{"argv": ["python3", "-c", "raise SystemExit(1)"], "cwd": "."}],
            },
        )

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch("sys.argv", ["run_loop.py", "--run-once"]):
                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        task_state = json.loads((self.root / "artifacts" / "agent" / "task-state.json").read_text(encoding="utf-8"))
        self.assertEqual(task_state["fail-task"]["status"], "blocked-needs-human-decision")

    def test_build_codex_exec_action_uses_low_model_env(self) -> None:
        task = {"id": "codex-task", "title": "Codex task", "model_hint": "low"}
        action = {"type": "codex_exec", "prompt": "Update docs", "cwd": "."}
        log_path = self.root / "artifacts" / "agent" / "runs" / "sample.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with mock.patch.dict(os.environ, {"CODEX_LOW_MODEL": "gpt-5.4-mini"}, clear=False):
            with mock.patch.object(self.loop_module, "resolve_codex_command", return_value=["/tmp/node", "/tmp/codex.js"]):
                argv, cwd, message_path, timeout_seconds, heartbeat_seconds, error = self.loop_module.build_action_invocation(
                    task, action, self.root, 1, log_path
                )

        self.assertIsNone(error)
        self.assertEqual(cwd, ".")
        self.assertIsNotNone(message_path)
        self.assertEqual(timeout_seconds, self.loop_module.DEFAULT_CODEX_EXEC_TIMEOUT_SECONDS)
        self.assertEqual(heartbeat_seconds, self.loop_module.DEFAULT_CODEX_EXEC_HEARTBEAT_SECONDS)
        self.assertEqual(argv[0], "/tmp/node")
        self.assertEqual(argv[1], "/tmp/codex.js")
        self.assertIn("--full-auto", argv)
        self.assertEqual(argv[-1], "Update docs")
        self.assertIn("gpt-5.4-mini", argv)

    def test_build_codex_exec_action_uses_explicit_timeout(self) -> None:
        task = {"id": "codex-task", "title": "Codex task", "model_hint": "low"}
        action = {"type": "codex_exec", "prompt": "Update docs", "cwd": ".", "timeout_seconds": 42}
        log_path = self.root / "artifacts" / "agent" / "runs" / "sample.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with mock.patch.object(self.loop_module, "resolve_codex_command", return_value=["/tmp/node", "/tmp/codex.js"]):
            argv, cwd, message_path, timeout_seconds, heartbeat_seconds, error = self.loop_module.build_action_invocation(
                task, action, self.root, 1, log_path
            )

        self.assertIsNone(error)
        self.assertEqual(cwd, ".")
        self.assertIsNotNone(message_path)
        self.assertEqual(timeout_seconds, 42)
        self.assertEqual(heartbeat_seconds, self.loop_module.DEFAULT_CODEX_EXEC_HEARTBEAT_SECONDS)
        self.assertEqual(argv[-1], "Update docs")

    def test_run_action_emits_heartbeat_before_completion(self) -> None:
        heartbeats: list[int] = []

        class FakeProcess:
            def __init__(self) -> None:
                self.pid = 4321
                self.returncode = 0
                self.communicate_calls = 0

            def communicate(self, timeout=None):
                self.communicate_calls += 1
                if self.communicate_calls == 1:
                    raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout)
                return ("done", "")

            def wait(self, timeout=None):
                return self.returncode

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

        fake_process = FakeProcess()
        with mock.patch.object(self.loop_module.subprocess, "Popen", return_value=fake_process):
            with mock.patch.object(self.loop_module.time, "monotonic", side_effect=[0, 0, 5, 5]):
                returncode, stdout, stderr, timed_out = self.loop_module.run_action(
                    ["/bin/echo", "ok"],
                    cwd=self.root,
                    timeout_seconds=None,
                    heartbeat_seconds=5,
                    heartbeat_callback=heartbeats.append,
                )

        self.assertEqual(returncode, 0)
        self.assertEqual(stdout, "done")
        self.assertEqual(stderr, "")
        self.assertFalse(timed_out)
        self.assertEqual(heartbeats, [5])

    def test_resolve_codex_bin_falls_back_to_nvm_install(self) -> None:
        fake_home = self.root / "home"
        fake_codex = fake_home / ".nvm" / "versions" / "node" / "v24.12.0" / "bin" / "codex"
        fake_codex.parent.mkdir(parents=True, exist_ok=True)
        fake_codex.write_text("#!/bin/sh\n", encoding="utf-8")
        fake_codex.chmod(0o755)

        with mock.patch.object(self.loop_module.Path, "home", return_value=fake_home):
            with mock.patch.object(self.loop_module.shutil, "which", return_value=None):
                resolved = self.loop_module.resolve_codex_bin()

        self.assertEqual(resolved, str(fake_codex))

    def test_resolve_codex_command_prefers_matching_node_binary(self) -> None:
        fake_home = self.root / "home"
        fake_node_dir = fake_home / ".nvm" / "versions" / "node" / "v24.12.0" / "bin"
        fake_node_dir.mkdir(parents=True, exist_ok=True)
        fake_codex = fake_node_dir / "codex"
        fake_node = fake_node_dir / "node"
        fake_codex.write_text("#!/usr/bin/env node\n", encoding="utf-8")
        fake_node.write_text("", encoding="utf-8")
        fake_codex.chmod(0o755)
        fake_node.chmod(0o755)

        with mock.patch.object(self.loop_module.Path, "home", return_value=fake_home):
            with mock.patch.object(self.loop_module.shutil, "which", return_value=None):
                command = self.loop_module.resolve_codex_command()

        self.assertEqual(command, [str(fake_node), str(fake_codex.resolve())])

    def test_run_once_skips_codex_exec_tasks_without_flag(self) -> None:
        self._write_task(
            "100-codex.json",
            {
                "id": "codex-task",
                "title": "Codex task",
                "priority": 100,
                "model_hint": "low",
                "actions": [{"type": "codex_exec", "prompt": "Update docs", "cwd": "."}],
            },
        )

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch("sys.argv", ["run_loop.py", "--run-once"]):
                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        status_payload = json.loads((self.root / "artifacts" / "agent" / "agent-status.json").read_text(encoding="utf-8"))
        task = next(item for item in status_payload["tasks"] if item["id"] == "codex-task")
        self.assertEqual(task["status"], "pending")
        self.assertEqual(status_payload["overall_state"], "READY")

    def test_codex_startup_timeout_schedules_retry(self) -> None:
        self._write_task(
            "100-codex-timeout.json",
            {
                "id": "codex-timeout",
                "title": "Codex timeout",
                "priority": 100,
                "retry_delay_seconds": 60,
                "actions": [
                    {
                        "type": "codex_exec",
                        "prompt": "Update docs",
                        "cwd": ".",
                        "timeout_seconds": 1,
                    }
                ],
            },
        )

        class FakeProcess:
            def __init__(self) -> None:
                self.pid = 1234
                self.returncode = -15
                self.communicate_calls = 0

            def communicate(self, timeout=None):
                self.communicate_calls += 1
                if self.communicate_calls == 1:
                    raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout, output="", stderr="")
                return ("", "")

            def wait(self, timeout=None):
                return self.returncode

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

        fake_process = FakeProcess()

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch.object(self.loop_module, "resolve_codex_command", return_value=["/tmp/node", "/tmp/codex.js"]):
                with mock.patch.object(self.loop_module.subprocess, "Popen", return_value=fake_process):
                    with mock.patch.object(self.loop_module.os, "killpg") as killpg_mock:
                        with mock.patch.object(self.loop_module.time, "monotonic", side_effect=[0, 0, 1, 1]):
                            with mock.patch("sys.argv", ["run_loop.py", "--run-once", "--allow-codex-exec"]):
                                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        self.assertTrue(killpg_mock.called)
        task_state = json.loads((self.root / "artifacts" / "agent" / "task-state.json").read_text(encoding="utf-8"))
        self.assertEqual(task_state["codex-timeout"]["status"], "retry-later")
        self.assertEqual(task_state["codex-timeout"]["last_result"], "retry-scheduled-startup-timeout")
        log_rel = task_state["codex-timeout"]["last_log"]
        log_text = (self.root / log_rel).read_text(encoding="utf-8")
        self.assertIn("[TIMEOUT] action exceeded 1 second(s) and was terminated.", log_text)
        self.assertIn("[STARTUP_TIMEOUT] no output, heartbeat, or last message was captured before timeout", log_text)

    def test_codex_timeout_with_heartbeat_uses_generic_timeout_result(self) -> None:
        self._write_task(
            "100-codex-timeout-heartbeat.json",
            {
                "id": "codex-timeout-heartbeat",
                "title": "Codex timeout heartbeat",
                "priority": 100,
                "retry_delay_seconds": 60,
                "actions": [
                    {
                        "type": "codex_exec",
                        "prompt": "Update docs",
                        "cwd": ".",
                        "timeout_seconds": 2,
                        "heartbeat_seconds": 1,
                    }
                ],
            },
        )

        class FakeProcess:
            def __init__(self) -> None:
                self.pid = 5678
                self.returncode = -15
                self.communicate_calls = 0

            def communicate(self, timeout=None):
                self.communicate_calls += 1
                if self.communicate_calls <= 2:
                    raise subprocess.TimeoutExpired(cmd=["codex"], timeout=timeout, output="", stderr="")
                return ("", "")

            def wait(self, timeout=None):
                return self.returncode

            def terminate(self):
                self.returncode = -15

            def kill(self):
                self.returncode = -9

        fake_process = FakeProcess()

        with mock.patch.object(self.loop_module, "repo_root", return_value=self.root):
            with mock.patch.object(self.loop_module, "resolve_codex_command", return_value=["/tmp/node", "/tmp/codex.js"]):
                with mock.patch.object(self.loop_module.subprocess, "Popen", return_value=fake_process):
                    with mock.patch.object(self.loop_module.os, "killpg") as killpg_mock:
                        with mock.patch.object(self.loop_module.time, "monotonic", side_effect=[0, 0, 1, 1, 1, 2, 2]):
                            with mock.patch("sys.argv", ["run_loop.py", "--run-once", "--allow-codex-exec"]):
                                exit_code = self.loop_module.main()

        self.assertEqual(exit_code, 0)
        self.assertTrue(killpg_mock.called)
        task_state = json.loads((self.root / "artifacts" / "agent" / "task-state.json").read_text(encoding="utf-8"))
        self.assertEqual(task_state["codex-timeout-heartbeat"]["status"], "retry-later")
        self.assertEqual(task_state["codex-timeout-heartbeat"]["last_result"], "retry-scheduled-timeout")
        log_rel = task_state["codex-timeout-heartbeat"]["last_log"]
        log_text = (self.root / log_rel).read_text(encoding="utf-8")
        self.assertIn("[HEARTBEAT] still running after 1 second(s)", log_text)

    def test_recover_stale_in_progress_task_to_retry_later(self) -> None:
        tasks = [
            {
                "id": "codex-task",
                "title": "Codex task",
                "max_attempts": 3,
            }
        ]
        task_state = {
            "codex-task": {
                "status": "in_progress",
                "attempts": 2,
            }
        }
        loop_state = {"current_task_id": "codex-task", "current_task_title": "Codex task", "recent_events": []}

        self.loop_module.recover_stale_in_progress_tasks(tasks, task_state, loop_state)

        self.assertIsNone(loop_state["current_task_id"])
        self.assertEqual(task_state["codex-task"]["status"], "retry-later")
        self.assertEqual(task_state["codex-task"]["last_result"], "recovered-from-stale-in-progress")

    def test_agent_status_groups_recent_failure_reasons(self) -> None:
        self._write_task(
            "100-codex-timeout.json",
            {
                "id": "codex-timeout",
                "title": "Codex timeout",
                "priority": 100,
                "actions": [{"type": "codex_exec", "prompt": "Update docs", "cwd": "."}],
            },
        )
        (self.root / "artifacts" / "agent" / "task-state.json").write_text(
            json.dumps(
                {
                    "codex-timeout": {
                        "status": "retry-later",
                        "attempts": 1,
                        "retry_after": "2026-03-17T20:15:00+00:00",
                        "last_started_at": "2026-03-17T20:00:00+00:00",
                        "last_finished_at": "2026-03-17T20:01:00+00:00",
                        "last_result": "retry-scheduled-startup-timeout",
                    }
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        payload = self.status_module.build_status_payload(self.root)

        self.assertEqual(payload["result_class_counts"]["startup-timeout"], 1)
        self.assertEqual(payload["result_class_counts"]["timeout"], 0)
        self.assertEqual(payload["attention_tasks"][0]["id"], "codex-timeout")
        self.assertEqual(payload["attention_tasks"][0]["last_result_class"], "startup-timeout")


if __name__ == "__main__":
    unittest.main(verbosity=2)
