#!/usr/bin/env python3
"""Deterministic governance tests for plan/validate/execute workflow."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import unittest
import uuid
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
            path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
