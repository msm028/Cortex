#!/usr/bin/env python3
"""Deterministic governance tests for plan/validate/execute workflow."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
import uuid
from unittest import mock
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
TEST_ROOT = REPO_ROOT / "artifacts" / "test"
AUDIT_DIR = REPO_ROOT / "artifacts" / "audit"


def canonical_json_text(data: object) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


class GovernanceWorkflowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        TEST_ROOT.mkdir(parents=True, exist_ok=True)
        AUDIT_DIR.mkdir(parents=True, exist_ok=True)

    def setUp(self) -> None:
        self.case_dir = TEST_ROOT / f"case-{uuid.uuid4().hex}"
        self.case_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self) -> None:
        shutil.rmtree(self.case_dir, ignore_errors=True)

    def _write_plan_with_sha(self, filename: str, plan: dict) -> Path:
        plan_path = self.case_dir / filename
        canonical = canonical_json_text(plan)
        digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        plan_path.write_text(canonical + "\n", encoding="utf-8")
        Path(str(plan_path) + ".sha256").write_text(digest + "\n", encoding="utf-8")
        return plan_path

    def _run_python(self, script_relative: str, *args: str) -> subprocess.CompletedProcess[str]:
        cmd = [sys.executable, str(REPO_ROOT / script_relative), *args]
        return subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, check=False)

    def _base_plan(self, action: dict, env: str = "dev") -> dict:
        return {
            "version": 1,
            "created_at": "2026-02-14T00:00:00Z",
            "env": env,
            "target": "local-repo",
            "actions": [action],
        }

    def _load_executor_module(self):
        module_path = REPO_ROOT / "ops" / "executor" / "execute_plan.py"
        spec = importlib.util.spec_from_file_location("execute_plan_module_for_tests", module_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_policy_deny_rm_rf(self) -> None:
        plan = self._base_plan(
            {
                "id": "deny-rm",
                "type": "shell",
                "cwd": ".",
                "cmd": ["rm", "-rf", "/"],
                "destructive": False,
            }
        )
        plan_path = self._write_plan_with_sha("deny-rm.json", plan)

        result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("decision=DENY", result.stdout)
        self.assertIn("denied by policy", result.stdout)

    def test_require_approval_missing(self) -> None:
        plan = self._base_plan(
            {
                "id": "needs-approval",
                "type": "shell",
                "cwd": ".",
                "cmd": ["git", "status"],
                "destructive": True,
            }
        )
        plan_path = self._write_plan_with_sha("approval-missing.json", plan)

        result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("decision=REQUIRE_APPROVAL", result.stdout)
        self.assertIn("Plan requires approval file", result.stdout)

    def test_approval_hash_binding(self) -> None:
        plan = self._base_plan(
            {
                "id": "approval-hash-binding",
                "type": "shell",
                "cwd": ".",
                "cmd": ["git", "status"],
                "destructive": True,
            }
        )
        plan_path = self._write_plan_with_sha("approval-hash-binding.json", plan)

        approve_result = self._run_python(
            "ops/plan/approve_plan.py",
            "--plan",
            str(plan_path),
            "--vaultwarden-item-id",
            "VW-TEST-ITEM-001",
        )
        self.assertEqual(approve_result.returncode, 0, msg=approve_result.stdout + approve_result.stderr)

        tampered_plan = self._base_plan(
            {
                "id": "approval-hash-binding",
                "type": "shell",
                "cwd": ".",
                "cmd": ["git", "status", "--short"],
                "destructive": True,
            }
        )
        self._write_plan_with_sha("approval-hash-binding.json", tampered_plan)

        validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
        self.assertNotEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)
        self.assertIn("Approval plan_sha256 mismatch", validate_result.stdout)

    def test_prod_requires_approval(self) -> None:
        plan = self._base_plan(
            {
                "id": "prod-needs-approval",
                "type": "shell",
                "cwd": ".",
                "cmd": ["make", "validate"],
                "destructive": False,
            },
            env="prod",
        )
        plan_path = self._write_plan_with_sha("prod-needs-approval.json", plan)

        result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))

        self.assertNotEqual(result.returncode, 0, msg=result.stdout + result.stderr)
        self.assertIn("decision=ALLOW", result.stdout)
        self.assertIn("Plan requires approval file", result.stdout)

    def test_approval_ttl_expired(self) -> None:
        plan = self._base_plan(
            {
                "id": "ttl-expired",
                "type": "shell",
                "cwd": ".",
                "cmd": ["echo", "ttl-test"],
                "destructive": True,
            },
            env="dev",
        )
        plan_path = self._write_plan_with_sha("ttl-expired.json", plan)

        approve_result = self._run_python(
            "ops/plan/approve_plan.py",
            "--plan",
            str(plan_path),
            "--vaultwarden-item-id",
            "VW-TEST-ITEM-003",
        )
        self.assertEqual(approve_result.returncode, 0, msg=approve_result.stdout + approve_result.stderr)

        approval_path = Path(str(plan_path) + ".approved")
        approval_path.write_text(
            "\n".join(
                [
                    "vaultwarden_item_id: VW-TEST-ITEM-003",
                    "plan_sha256: " + hashlib.sha256(canonical_json_text(plan).encode("utf-8")).hexdigest(),
                    "approved_at: 2026-01-01T00:00:00Z",
                    "",
                ]
            ),
            encoding="utf-8",
        )

        validate_result = self._run_python(
            "ops/plan/validate_plan.py",
            "--plan",
            str(plan_path),
            "--now-utc",
            "2026-01-02T00:00:01Z",
        )
        self.assertNotEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)
        self.assertIn("Approval TTL expired", validate_result.stdout)

    def test_execute_writes_audit(self) -> None:
        plan = self._base_plan(
            {
                "id": "execute-audit-safe",
                "type": "shell",
                "cwd": ".",
                "cmd": ["echo", "governance-test"],
                "destructive": True,
            }
        )
        plan_path = self._write_plan_with_sha("execute-audit-safe.json", plan)
        before = set(AUDIT_DIR.glob("*.audit.json"))

        approve_result = self._run_python(
            "ops/plan/approve_plan.py",
            "--plan",
            str(plan_path),
            "--vaultwarden-item-id",
            "VW-TEST-ITEM-002",
        )
        self.assertEqual(approve_result.returncode, 0, msg=approve_result.stdout + approve_result.stderr)

        execute_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
        self.assertEqual(execute_result.returncode, 0, msg=execute_result.stdout + execute_result.stderr)
        self.assertIn("[PASS] Plan executed successfully", execute_result.stdout)

        after = set(AUDIT_DIR.glob("*.audit.json"))
        new_files = after - before
        self.assertTrue(new_files, "expected at least one new audit file")

        related = [path for path in new_files if path.name.startswith(plan_path.name + ".")]
        self.assertTrue(related, "expected an audit file for the executed plan")

        for path in related:
            payload = json.loads(path.read_text(encoding="utf-8"))
            approval = payload.get("approval")
            self.assertIsInstance(approval, dict)
            self.assertEqual(approval.get("ttl_seconds"), 86400)
            self.assertEqual(approval.get("is_expired"), False)
            path.unlink(missing_ok=True)

    def test_infra_demo_dry_run_and_exec_gate(self) -> None:
        plan = {
            "version": 1,
            "created_at": "2026-02-14T00:00:00Z",
            "env": "dev",
            "target": "local-repo",
            "actions": [
                {
                    "id": "docker-config",
                    "type": "docker_compose",
                    "project_dir": "bootstrap/compose/demo",
                    "args": ["config"],
                    "destructive": False,
                },
                {
                    "id": "terraform-fmt-check",
                    "type": "terraform",
                    "workdir": "infra/modules/demo",
                    "args": ["fmt", "-check"],
                    "destructive": False,
                },
            ],
        }
        plan_path = self._write_plan_with_sha("infra-demo.json", plan)
        before = set(AUDIT_DIR.glob("*.audit.json"))

        validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
        self.assertEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)
        self.assertIn("decision=ALLOW", validate_result.stdout)

        dry_run_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
        self.assertEqual(dry_run_result.returncode, 0, msg=dry_run_result.stdout + dry_run_result.stderr)
        self.assertIn("[PASS] Plan executed successfully", dry_run_result.stdout)

        after_dry_run = set(AUDIT_DIR.glob("*.audit.json"))
        dry_run_new = after_dry_run - before
        self.assertTrue(dry_run_new, "expected a new audit file from dry-run execution")

        dry_run_related = [path for path in dry_run_new if path.name.startswith(plan_path.name + ".")]
        self.assertTrue(dry_run_related, "expected dry-run audit file for infra plan")
        dry_run_payload = json.loads(dry_run_related[0].read_text(encoding="utf-8"))
        self.assertEqual(dry_run_payload.get("dry_run"), True)

        no_dry_run_result = self._run_python(
            "ops/executor/execute_plan.py",
            "--plan",
            str(plan_path),
            "--dry-run",
            "false",
        )
        self.assertNotEqual(no_dry_run_result.returncode, 0, msg=no_dry_run_result.stdout + no_dry_run_result.stderr)
        self.assertIn("Infra execution refused", no_dry_run_result.stdout + no_dry_run_result.stderr)

        final_files = set(AUDIT_DIR.glob("*.audit.json"))
        for path in (final_files - before):
            if path.name.startswith(plan_path.name + "."):
                path.unlink(missing_ok=True)

    def test_bootstrap_core_template_dry_run(self) -> None:
        prefix = f"test-bootstrap-core-{uuid.uuid4().hex[:8]}"
        mkplan_result = self._run_python(
            "ops/plan/mkplan.py",
            "--template",
            "bootstrap-core-dry-run",
            "--name-prefix",
            prefix,
        )
        self.assertEqual(mkplan_result.returncode, 0, msg=mkplan_result.stdout + mkplan_result.stderr)

        plan_line = next(
            (line for line in mkplan_result.stdout.splitlines() if line.startswith("[PASS] Plan created: ")),
            "",
        )
        self.assertTrue(plan_line, msg=mkplan_result.stdout)
        plan_rel = plan_line.split(": ", 1)[1].strip()
        plan_path = REPO_ROOT / plan_rel

        try:
            validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
            self.assertEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)

            before = set(AUDIT_DIR.glob("*.audit.json"))
            execute_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
            self.assertEqual(execute_result.returncode, 0, msg=execute_result.stdout + execute_result.stderr)

            after = set(AUDIT_DIR.glob("*.audit.json"))
            new_files = after - before
            related = [path for path in new_files if path.name.startswith(plan_path.name + ".")]
            self.assertTrue(related, "expected bootstrap-core audit file")

            payload = json.loads(related[0].read_text(encoding="utf-8"))
            self.assertEqual(payload.get("dry_run"), True)
            action_results = payload.get("action_results", [])
            self.assertTrue(action_results, "expected action results in audit payload")
            self.assertEqual(action_results[0].get("type"), "docker_compose")
            for path in related:
                path.unlink(missing_ok=True)
        finally:
            plan_path.unlink(missing_ok=True)
            Path(str(plan_path) + ".sha256").unlink(missing_ok=True)
            Path(str(plan_path) + ".approved").unlink(missing_ok=True)

    def test_bootstrap_core_up_down_templates_dry_run(self) -> None:
        for template in ("bootstrap-core-up", "bootstrap-core-down"):
            prefix = f"test-{template}-{uuid.uuid4().hex[:8]}"
            mkplan_result = self._run_python(
                "ops/plan/mkplan.py",
                "--template",
                template,
                "--name-prefix",
                prefix,
            )
            self.assertEqual(mkplan_result.returncode, 0, msg=mkplan_result.stdout + mkplan_result.stderr)

            plan_line = next(
                (line for line in mkplan_result.stdout.splitlines() if line.startswith("[PASS] Plan created: ")),
                "",
            )
            self.assertTrue(plan_line, msg=mkplan_result.stdout)
            plan_rel = plan_line.split(": ", 1)[1].strip()
            plan_path = REPO_ROOT / plan_rel

            try:
                approve_result = self._run_python(
                    "ops/plan/approve_plan.py",
                    "--plan",
                    str(plan_path),
                    "--vaultwarden-item-id",
                    f"VW-TEST-{template.upper()}-001",
                )
                self.assertEqual(approve_result.returncode, 0, msg=approve_result.stdout + approve_result.stderr)

                validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
                self.assertEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)

                before = set(AUDIT_DIR.glob("*.audit.json"))
                execute_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
                self.assertEqual(execute_result.returncode, 0, msg=execute_result.stdout + execute_result.stderr)

                after = set(AUDIT_DIR.glob("*.audit.json"))
                new_files = after - before
                related = [path for path in new_files if path.name.startswith(plan_path.name + ".")]
                self.assertTrue(related, f"expected audit file for {template}")

                payload = json.loads(related[0].read_text(encoding="utf-8"))
                self.assertEqual(payload.get("dry_run"), True)
                action_results = payload.get("action_results", [])
                self.assertTrue(action_results, "expected action results in audit payload")
                self.assertEqual(action_results[0].get("type"), "docker_compose")

                for path in related:
                    path.unlink(missing_ok=True)
            finally:
                plan_path.unlink(missing_ok=True)
                Path(str(plan_path) + ".sha256").unlink(missing_ok=True)
                Path(str(plan_path) + ".approved").unlink(missing_ok=True)

    def test_edge_dry_run_template(self) -> None:
        prefix = f"test-edge-dry-run-{uuid.uuid4().hex[:8]}"
        mkplan_result = self._run_python(
            "ops/plan/mkplan.py",
            "--template",
            "edge-dry-run",
            "--name-prefix",
            prefix,
        )
        self.assertEqual(mkplan_result.returncode, 0, msg=mkplan_result.stdout + mkplan_result.stderr)

        plan_line = next(
            (line for line in mkplan_result.stdout.splitlines() if line.startswith("[PASS] Plan created: ")),
            "",
        )
        self.assertTrue(plan_line, msg=mkplan_result.stdout)
        plan_rel = plan_line.split(": ", 1)[1].strip()
        plan_path = REPO_ROOT / plan_rel

        try:
            validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
            self.assertEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)

            before = set(AUDIT_DIR.glob("*.audit.json"))
            execute_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
            self.assertEqual(execute_result.returncode, 0, msg=execute_result.stdout + execute_result.stderr)

            after = set(AUDIT_DIR.glob("*.audit.json"))
            new_files = after - before
            related = [path for path in new_files if path.name.startswith(plan_path.name + ".")]
            self.assertTrue(related, "expected edge dry-run audit file")

            payload = json.loads(related[0].read_text(encoding="utf-8"))
            self.assertEqual(payload.get("dry_run"), True)
            action_results = payload.get("action_results", [])
            self.assertTrue(action_results, "expected action results in edge audit payload")
            self.assertEqual(action_results[0].get("type"), "docker_compose")

            for path in related:
                path.unlink(missing_ok=True)
        finally:
            plan_path.unlink(missing_ok=True)
            Path(str(plan_path) + ".sha256").unlink(missing_ok=True)
            Path(str(plan_path) + ".approved").unlink(missing_ok=True)

    def test_edge_up_down_templates_dry_run(self) -> None:
        for template in ("edge-up", "edge-down"):
            prefix = f"test-{template}-{uuid.uuid4().hex[:8]}"
            mkplan_result = self._run_python(
                "ops/plan/mkplan.py",
                "--template",
                template,
                "--name-prefix",
                prefix,
            )
            self.assertEqual(mkplan_result.returncode, 0, msg=mkplan_result.stdout + mkplan_result.stderr)

            plan_line = next(
                (line for line in mkplan_result.stdout.splitlines() if line.startswith("[PASS] Plan created: ")),
                "",
            )
            self.assertTrue(plan_line, msg=mkplan_result.stdout)
            plan_rel = plan_line.split(": ", 1)[1].strip()
            plan_path = REPO_ROOT / plan_rel

            try:
                approve_result = self._run_python(
                    "ops/plan/approve_plan.py",
                    "--plan",
                    str(plan_path),
                    "--vaultwarden-item-id",
                    f"VW-TEST-{template.upper()}-001",
                )
                self.assertEqual(approve_result.returncode, 0, msg=approve_result.stdout + approve_result.stderr)

                validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
                self.assertEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)

                before = set(AUDIT_DIR.glob("*.audit.json"))
                execute_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
                self.assertEqual(execute_result.returncode, 0, msg=execute_result.stdout + execute_result.stderr)

                after = set(AUDIT_DIR.glob("*.audit.json"))
                new_files = after - before
                related = [path for path in new_files if path.name.startswith(plan_path.name + ".")]
                self.assertTrue(related, f"expected audit file for {template}")

                payload = json.loads(related[0].read_text(encoding="utf-8"))
                self.assertEqual(payload.get("dry_run"), True)
                action_results = payload.get("action_results", [])
                self.assertTrue(action_results, "expected action results in edge up/down audit payload")
                self.assertEqual(action_results[0].get("type"), "docker_compose")

                for path in related:
                    path.unlink(missing_ok=True)
            finally:
                plan_path.unlink(missing_ok=True)
                Path(str(plan_path) + ".sha256").unlink(missing_ok=True)
                Path(str(plan_path) + ".approved").unlink(missing_ok=True)

    def test_stack_status_template_dry_run(self) -> None:
        prefix = f"test-stack-status-{uuid.uuid4().hex[:8]}"
        mkplan_result = self._run_python(
            "ops/plan/mkplan.py",
            "--template",
            "stack-status",
            "--name-prefix",
            prefix,
        )
        self.assertEqual(mkplan_result.returncode, 0, msg=mkplan_result.stdout + mkplan_result.stderr)

        plan_line = next(
            (line for line in mkplan_result.stdout.splitlines() if line.startswith("[PASS] Plan created: ")),
            "",
        )
        self.assertTrue(plan_line, msg=mkplan_result.stdout)
        plan_rel = plan_line.split(": ", 1)[1].strip()
        plan_path = REPO_ROOT / plan_rel

        try:
            validate_result = self._run_python("ops/plan/validate_plan.py", "--plan", str(plan_path))
            self.assertEqual(validate_result.returncode, 0, msg=validate_result.stdout + validate_result.stderr)

            before = set(AUDIT_DIR.glob("*.audit.json"))
            execute_result = self._run_python("ops/executor/execute_plan.py", "--plan", str(plan_path))
            self.assertEqual(execute_result.returncode, 0, msg=execute_result.stdout + execute_result.stderr)

            after = set(AUDIT_DIR.glob("*.audit.json"))
            new_files = after - before
            related = [path for path in new_files if path.name.startswith(plan_path.name + ".")]
            self.assertTrue(related, "expected stack-status audit file")

            payload = json.loads(related[0].read_text(encoding="utf-8"))
            self.assertEqual(payload.get("dry_run"), True)
            action_results = payload.get("action_results", [])
            self.assertTrue(action_results, "expected action results in stack status audit payload")
            self.assertEqual(action_results[0].get("type"), "shell")
            generated_plan = json.loads(plan_path.read_text(encoding="utf-8"))
            action_ids = [action.get("id") for action in generated_plan.get("actions", [])]
            self.assertEqual(
                action_ids,
                [
                    "stack-ps-core-edge",
                    "stack-smoke",
                    "caddy_listen_check",
                    "route_check_vault",
                    "route_check_minio",
                ],
            )
            result_ids = [item.get("id") for item in action_results]
            self.assertEqual(
                result_ids,
                [
                    "stack-ps-core-edge",
                    "stack-smoke",
                    "caddy_listen_check",
                    "route_check_vault",
                    "route_check_minio",
                ],
            )

            for path in related:
                path.unlink(missing_ok=True)
        finally:
            plan_path.unlink(missing_ok=True)
            Path(str(plan_path) + ".sha256").unlink(missing_ok=True)
            Path(str(plan_path) + ".approved").unlink(missing_ok=True)

    def test_executor_docker_compose_argv_order(self) -> None:
        module = self._load_executor_module()
        action = {
            "id": "compose-up",
            "type": "docker_compose",
            "project_dir": "bootstrap/compose/edge",
            "args": ["up", "-d"],
            "destructive": False,
        }

        completed = subprocess.CompletedProcess(
            args=["docker", "compose", "up", "-d"],
            returncode=0,
            stdout="ok\n",
            stderr="",
        )
        with mock.patch.object(module.subprocess, "run", return_value=completed) as run_mock:
            result = module.run_action(action, policy_result=None, dry_run=False, allow_infra_exec=True)

        run_mock.assert_called_once()
        called_cmd = run_mock.call_args.args[0]
        self.assertEqual(called_cmd, ["docker", "compose", "up", "-d"])
        self.assertEqual(result["cmd"], ["docker", "compose", "up", "-d"])
        self.assertEqual(result["exit_code"], 0)

    def test_executor_shell_json_status_fields(self) -> None:
        module = self._load_executor_module()
        action = {
            "id": "route_check_minio",
            "type": "shell",
            "cwd": ".",
            "cmd": ["python3", "-c", "print('noop')"],
            "destructive": False,
        }
        completed = subprocess.CompletedProcess(
            args=action["cmd"],
            returncode=0,
            stdout='{"status_code":302,"message":"minio route check passed"}\n',
            stderr="",
        )
        with mock.patch.object(module.subprocess, "run", return_value=completed):
            result = module.run_action(action, policy_result=None, dry_run=False, allow_infra_exec=True)

        self.assertEqual(result["exit_code"], 0)
        self.assertEqual(result.get("status_code"), 302)
        self.assertEqual(result.get("message"), "minio route check passed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
