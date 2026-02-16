#!/usr/bin/env python3
"""Unit tests for mkplan helpers."""

from __future__ import annotations

import unittest
from unittest import mock
import os
import json
import pathlib
import tempfile

from ops.executor import execute_plan
from ops.plan import mkplan


class MkplanHealthPollingTests(unittest.TestCase):
    @mock.patch("ops.plan.mkplan.time.sleep")
    @mock.patch("ops.plan.mkplan.time.monotonic")
    @mock.patch("ops.plan.mkplan.subprocess.check_output")
    def test_poll_core_container_health_waits_for_healthy(
        self,
        mock_check_output: mock.Mock,
        mock_monotonic: mock.Mock,
        mock_sleep: mock.Mock,
    ) -> None:
        mock_check_output.side_effect = [
            '"starting"\n"starting"\n"starting"\n',
            '"healthy"\n"healthy"\n"healthy"\n',
        ]
        mock_monotonic.side_effect = [0.0, 1.0, 2.0]

        exit_code = mkplan.poll_core_container_health()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_check_output.call_count, 2)
        mock_sleep.assert_called_once_with(mkplan.CORE_HEALTH_POLL_INTERVAL_SECONDS)

    @mock.patch("ops.plan.mkplan.poll_container_health", return_value=0)
    @mock.patch(
        "ops.plan.mkplan.list_health_configured_stack_containers",
        return_value=["core-postgres-1", "core-minio-1"],
    )
    @mock.patch(
        "ops.plan.mkplan.list_running_stack_containers",
        return_value=["core-postgres-1", "core-minio-1", "edge-caddy-1"],
    )
    def test_run_stack_status_smoke_checks_passes_when_health_and_caddy_ok(
        self,
        mock_running: mock.Mock,
        mock_health_configured: mock.Mock,
        mock_poll: mock.Mock,
    ) -> None:
        exit_code = mkplan.run_stack_status_smoke_checks()

        self.assertEqual(exit_code, 0)
        mock_running.assert_called_once_with()
        mock_health_configured.assert_called_once_with(["core-postgres-1", "core-minio-1", "edge-caddy-1"])
        mock_poll.assert_called_once_with(
            ["core-postgres-1", "core-minio-1"],
            label="stack health-managed containers",
        )

    @mock.patch("ops.plan.mkplan.poll_container_health", return_value=0)
    @mock.patch(
        "ops.plan.mkplan.list_health_configured_stack_containers",
        return_value=["core-postgres-1"],
    )
    @mock.patch("ops.plan.mkplan.list_running_stack_containers", return_value=["core-postgres-1"])
    def test_run_stack_status_smoke_checks_fails_when_caddy_missing(
        self,
        _mock_running: mock.Mock,
        _mock_health_configured: mock.Mock,
        _mock_poll: mock.Mock,
    ) -> None:
        exit_code = mkplan.run_stack_status_smoke_checks()
        self.assertEqual(exit_code, 1)

    @mock.patch("ops.plan.mkplan.get_edge_caddy_ip", return_value="172.22.0.2")
    @mock.patch("ops.plan.mkplan.socket.create_connection")
    def test_run_caddy_listen_check_passes(
        self,
        mock_connect: mock.Mock,
        _mock_ip: mock.Mock,
    ) -> None:
        mock_connect.return_value = mock.MagicMock()
        self.assertEqual(mkplan.run_caddy_listen_check(), 0)

    @mock.patch("ops.plan.mkplan.get_edge_caddy_ip", return_value="172.22.0.2")
    @mock.patch("ops.plan.mkplan.http.client.HTTPConnection")
    def test_run_caddy_route_check_passes_on_non_404_non_5xx(
        self,
        mock_conn_cls: mock.Mock,
        _mock_ip: mock.Mock,
    ) -> None:
        conn = mock_conn_cls.return_value
        response = mock.Mock()
        response.status = 302
        response.read.return_value = b""
        conn.getresponse.return_value = response
        with mock.patch.dict(os.environ, {"PUBLIC_DOMAIN": "thecortexstack.com"}, clear=False):
            self.assertEqual(mkplan.run_caddy_route_check("vault"), 0)

    @mock.patch("ops.plan.mkplan.get_edge_caddy_ip", return_value="172.22.0.2")
    @mock.patch("ops.plan.mkplan.http.client.HTTPConnection")
    def test_run_caddy_route_check_fails_on_5xx(
        self,
        mock_conn_cls: mock.Mock,
        _mock_ip: mock.Mock,
    ) -> None:
        conn = mock_conn_cls.return_value
        response = mock.Mock()
        response.status = 503
        response.read.return_value = b""
        conn.getresponse.return_value = response
        with mock.patch.dict(os.environ, {"PUBLIC_DOMAIN": "thecortexstack.com"}, clear=False):
            self.assertEqual(mkplan.run_caddy_route_check("minio"), 1)

    @mock.patch("ops.plan.mkplan.http.client.HTTPSConnection")
    def test_check_ingress_host_passes_with_cloudflare_headers(self, mock_conn_cls: mock.Mock) -> None:
        conn = mock_conn_cls.return_value
        response = mock.Mock()
        response.status = 302
        response.getheader.side_effect = lambda key, default="": {
            "server": "cloudflare",
            "cf-ray": "abc123",
        }.get(key.lower(), default)
        response.read.return_value = b""
        conn.getresponse.return_value = response
        with mock.patch.dict(os.environ, {"PUBLIC_DOMAIN": "thecortexstack.com"}, clear=False):
            result = mkplan.check_ingress_host("vault")
        self.assertEqual(result["status_code"], 302)
        self.assertEqual(result["server"], "cloudflare")
        self.assertEqual(result["cf_ray"], "abc123")
        self.assertEqual(result["passed"], True)

    @mock.patch("ops.plan.mkplan.check_ingress_host")
    def test_run_ingress_status_summary_prints_single_line(self, mock_check: mock.Mock) -> None:
        mock_check.side_effect = [
            {"passed": True},
            {"passed": False},
        ]
        with mock.patch("builtins.print") as print_mock:
            exit_code = mkplan.run_ingress_status_summary()
        self.assertEqual(exit_code, 1)
        print_mock.assert_called_once_with("INGRESS STATUS: FAIL")


class MkplanTemplateTests(unittest.TestCase):
    def test_backup_core_template_generates_plan_with_backup_action(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(mkplan.REPO_ROOT / "plans")) as tmpdir:
            with mock.patch.object(mkplan, "PLANS_DIR", pathlib.Path(tmpdir)):
                with mock.patch("sys.argv", ["mkplan.py", "--template", "backup-core", "--name-prefix", "plan"]):
                    exit_code = mkplan.main()
            self.assertEqual(exit_code, 0)
            plan_files = sorted(pathlib.Path(tmpdir).glob("plan-*.json"))
            self.assertEqual(len(plan_files), 1)
            payload = json.loads(plan_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["actions"][0]["id"], "backup-core")
            self.assertEqual(payload["actions"][0]["cmd"][0:2], ["python3", "-c"])

    def test_restore_test_template_generates_plan_with_restore_action(self) -> None:
        with tempfile.TemporaryDirectory(dir=str(mkplan.REPO_ROOT / "plans")) as tmpdir:
            with mock.patch.object(mkplan, "PLANS_DIR", pathlib.Path(tmpdir)):
                with mock.patch("sys.argv", ["mkplan.py", "--template", "restore-test", "--name-prefix", "plan"]):
                    exit_code = mkplan.main()
            self.assertEqual(exit_code, 0)
            plan_files = sorted(pathlib.Path(tmpdir).glob("plan-*.json"))
            self.assertEqual(len(plan_files), 1)
            payload = json.loads(plan_files[0].read_text(encoding="utf-8"))
            self.assertEqual(payload["actions"][0]["id"], "restore-test")
            self.assertEqual(payload["actions"][0]["cmd"][0:2], ["python3", "-c"])

    def test_backup_core_action_dry_run_renders_without_shell_execution(self) -> None:
        action = mkplan.build_backup_core_plan("2026-02-16T00:00:00Z")["actions"][0]
        with mock.patch("ops.executor.execute_plan.subprocess.run") as mock_run:
            result = execute_plan.run_action(
                action=action,
                policy_result=None,
                dry_run=True,
                allow_infra_exec=False,
            )
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("DRY RUN: would execute", result["stdout"])
        mock_run.assert_not_called()

    def test_restore_test_action_dry_run_renders_without_shell_execution(self) -> None:
        action = mkplan.build_restore_test_plan("2026-02-16T00:00:00Z")["actions"][0]
        with mock.patch("ops.executor.execute_plan.subprocess.run") as mock_run:
            result = execute_plan.run_action(
                action=action,
                policy_result=None,
                dry_run=True,
                allow_infra_exec=False,
            )
        self.assertEqual(result["exit_code"], 0)
        self.assertIn("DRY RUN: would execute", result["stdout"])
        mock_run.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
