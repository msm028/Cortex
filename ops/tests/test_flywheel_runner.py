#!/usr/bin/env python3
"""Unit tests for the flywheel runner safety gate."""

from __future__ import annotations

import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_flywheel_module():
    module_path = REPO_ROOT / "skills" / "flywheel-runner" / "run-flywheel.py"
    spec = importlib.util.spec_from_file_location("run_flywheel_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load flywheel module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FlywheelRunnerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_flywheel_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / ".codex").mkdir(parents=True)
        (self.root / "plans").mkdir(parents=True)
        (self.root / ".codex" / "config.toml").write_text(
            'infra_step_examples = ["tofu apply", "docker compose down on hosts"]\n',
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _write_plan(self, name: str, payload: dict) -> Path:
        path = self.root / "plans" / name
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_risky_exec_requires_confirm_risk(self) -> None:
        plan_path = self._write_plan(
            "risky.json",
            {"actions": [{"cmd": ["sh", "-c", "tofu apply -auto-approve"]}]},
        )

        stdout = io.StringIO()
        with mock.patch.object(self.module, "repo_root", return_value=self.root):
            with mock.patch.object(self.module, "run_cmd") as run_cmd:
                with mock.patch(
                    "sys.argv",
                    [
                        "run-flywheel.py",
                        "--message",
                        "test",
                        "--plan",
                        str(plan_path),
                        "--exec",
                        "echo APPLY {plan}",
                        "--yes",
                        "--no-validate",
                    ],
                ):
                    with redirect_stdout(stdout):
                        exit_code = self.module.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("[RISK] matched", stdout.getvalue())
        self.assertIn("[SAFE-EXIT] risk indicators found", stdout.getvalue())
        run_cmd.assert_not_called()

    def test_risky_exec_runs_with_confirm_risk(self) -> None:
        plan_path = self._write_plan(
            "risky.json",
            {"actions": [{"cmd": ["sh", "-c", "tofu apply -auto-approve"]}]},
        )

        stdout = io.StringIO()
        with mock.patch.object(self.module, "repo_root", return_value=self.root):
            with mock.patch.object(self.module, "run_cmd") as run_cmd:
                with mock.patch(
                    "sys.argv",
                    [
                        "run-flywheel.py",
                        "--message",
                        "test",
                        "--plan",
                        str(plan_path),
                        "--exec",
                        "echo APPLY {plan}",
                        "--yes",
                        "--confirm-risk",
                        "--no-validate",
                    ],
                ):
                    with redirect_stdout(stdout):
                        exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertIn("[RISK] matched", stdout.getvalue())
        self.assertEqual(run_cmd.call_count, 2)
        self.assertEqual(run_cmd.call_args_list[0].args[0], ["echo", "APPLY", str(plan_path)])
        self.assertEqual(
            run_cmd.call_args_list[1].args[0],
            ["python3", "skills/update-docs/update-docs.py", "--message", "test (plan: risky.json)", "--no-validate"],
        )

    def test_safe_exec_does_not_require_confirm_risk(self) -> None:
        plan_path = self._write_plan(
            "safe.json",
            {"actions": [{"cmd": ["echo", "hello"]}]},
        )

        with mock.patch.object(self.module, "repo_root", return_value=self.root):
            with mock.patch.object(self.module, "run_cmd") as run_cmd:
                with mock.patch(
                    "sys.argv",
                    [
                        "run-flywheel.py",
                        "--message",
                        "safe",
                        "--plan",
                        str(plan_path),
                        "--exec",
                        "echo APPLY {plan}",
                        "--yes",
                        "--no-validate",
                    ],
                ):
                    exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(run_cmd.call_count, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
