#!/usr/bin/env python3
"""Unit tests for the ops status page generator."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_ops_status_module():
    module_path = REPO_ROOT / "skills" / "ops-status" / "update-ops-status.py"
    spec = importlib.util.spec_from_file_location("update_ops_status_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load ops-status module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class OpsStatusTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_ops_status_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "docs").mkdir(parents=True)
        (self.root / "plans").mkdir(parents=True)
        (self.root / "artifacts" / "audit").mkdir(parents=True)
        (self.root / "artifacts" / "logs").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_render_status_page_includes_latest_plan_audit_and_endpoints(self) -> None:
        (self.root / "docs" / "inventory.md").write_text(
            "\n".join(
                [
                    "# Inventory",
                    "",
                    "## Endpoints",
                    "",
                    "- `http://cortex-control:8085` - hosted wiki",
                    "- `http://vault.thecortexstack.com` - Vaultwarden",
                    "",
                    "## Source Of Truth Links",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "plans" / "plan-1.json").write_text('{"actions":[]}\n', encoding="utf-8")
        (self.root / "artifacts" / "audit" / "plan-1.json.20260302T100000Z.audit.json").write_text(
            json.dumps(
                {
                    "plan": "plans/plan-1.json",
                    "status": "passed",
                    "executed_at": "2026-03-02T10:00:00Z",
                    "action_results": [{"id": "backup-core"}],
                }
            ),
            encoding="utf-8",
        )
        (self.root / "artifacts" / "logs" / "backup-core-20260302T100000Z.log").write_text(
            "[STEP] restic-backup\nBACKUP-CORE: PASS\n",
            encoding="utf-8",
        )
        (self.root / "artifacts" / "logs" / "restore-test-20260302T110000Z.log").write_text(
            "[STEP] restore\nRESTORE-TEST: FAIL\n",
            encoding="utf-8",
        )

        with mock.patch.object(self.module, "now_local_stamp", return_value="2026-03-02 12:34"):
            rendered = self.module.render_status_page(self.root)

        self.assertIn("# Ops Status", rendered)
        self.assertIn("`plan-1.json`", rendered)
        self.assertIn("`PASSED`", rendered)
        self.assertIn("`PASS`", rendered)
        self.assertIn("`FAIL`", rendered)
        self.assertIn("`http://cortex-control:8085` - hosted wiki", rendered)

    def test_main_writes_default_output(self) -> None:
        (self.root / "docs" / "inventory.md").write_text("# Inventory\n", encoding="utf-8")

        with mock.patch.object(self.module, "repo_root", return_value=self.root):
            with mock.patch("sys.argv", ["update-ops-status.py"]):
                exit_code = self.module.main()

        self.assertEqual(exit_code, 0)
        self.assertTrue((self.root / "docs" / "ops-status.md").is_file())

    def test_action_summary_falls_back_to_audit_status(self) -> None:
        result = self.module.action_summary(
            {"name": "backup.log", "status": "UNKNOWN", "mtime": "2026-03-02 10:00"},
            {"name": "backup.audit.json", "status": "PASSED", "executed_at": "2026-03-02T10:00:00Z"},
        )

        self.assertEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main(verbosity=2)
