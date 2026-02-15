#!/usr/bin/env python3
"""Unit tests for Vaultwarden environment injector."""

from __future__ import annotations

import importlib.util
import io
import json
import os
import pathlib
import subprocess
import unittest
from contextlib import redirect_stdout
from unittest import mock


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_vw_module():
    module_path = REPO_ROOT / "ops" / "bin" / "vw_env.py"
    spec = importlib.util.spec_from_file_location("vw_env_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load vw_env module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class VaultwardenEnvTests(unittest.TestCase):
    def test_extract_value_sources(self) -> None:
        module = load_vw_module()
        item = {
            "login": {"username": "alice", "password": "s3cr3t"},
            "fields": [{"name": "TOKEN", "value": "abc"}],
        }
        self.assertEqual(module.extract_value(item, "login.username"), "alice")
        self.assertEqual(module.extract_value(item, "login.password"), "s3cr3t")
        self.assertEqual(module.extract_value(item, "field:TOKEN"), "abc")

    @mock.patch("shutil.which", return_value="/usr/bin/bw")
    @mock.patch.dict(os.environ, {"BW_SESSION": "session-token", "BW_FOO": "remove-me"}, clear=False)
    def test_run_command_injects_env_without_printing_values(self, _mock_which: mock.Mock) -> None:
        module = load_vw_module()
        mapping = {
            "POSTGRES_USER": {"item_id": "item-1", "source": "login.username"},
            "POSTGRES_PASSWORD": {"item_id": "item-2", "source": "login.password"},
            "TUNNEL_TOKEN": {"item_id": "item-3", "source": "field:TUNNEL_TOKEN"},
        }
        secret_password = "ultra-secret-password"
        secret_token = "ultra-secret-token"

        def fake_run(cmd, **kwargs):
            if cmd[:3] == ["bw", "get", "item"]:
                item_id = cmd[3]
                if item_id == "item-1":
                    payload = {"login": {"username": "dbuser"}}
                elif item_id == "item-2":
                    payload = {"login": {"password": secret_password}}
                elif item_id == "item-3":
                    payload = {"fields": [{"name": "TUNNEL_TOKEN", "value": secret_token}]}
                else:
                    payload = {}
                return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(payload), stderr="")
            self.assertEqual(cmd, ["echo", "ok"])
            env = kwargs.get("env", {})
            self.assertEqual(env.get("POSTGRES_USER"), "dbuser")
            self.assertEqual(env.get("POSTGRES_PASSWORD"), secret_password)
            self.assertEqual(env.get("TUNNEL_TOKEN"), secret_token)
            self.assertNotIn("BW_SESSION", env)
            self.assertNotIn("BW_FOO", env)
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        with (
            mock.patch.object(module, "load_mapping", return_value=mapping),
            mock.patch.object(module.subprocess, "run", side_effect=fake_run),
            redirect_stdout(io.StringIO()) as buf,
        ):
            code = module.run_command(["echo", "ok"])

        output = buf.getvalue()
        self.assertEqual(code, 0)
        self.assertIn("POSTGRES_USER: OK", output)
        self.assertIn("POSTGRES_PASSWORD: OK", output)
        self.assertIn("TUNNEL_TOKEN: OK", output)
        self.assertNotIn(secret_password, output)
        self.assertNotIn(secret_token, output)

    @mock.patch("shutil.which", return_value=None)
    @mock.patch.dict(os.environ, {}, clear=False)
    def test_check_reports_missing_prereqs(self, _mock_which: mock.Mock) -> None:
        module = load_vw_module()
        mapping = {
            "POSTGRES_USER": {"item_id": "REPLACE_ME", "source": "login.username"},
        }
        with (
            mock.patch.object(module, "load_mapping", return_value=mapping),
            redirect_stdout(io.StringIO()) as buf,
        ):
            code = module.run_check()
        output = buf.getvalue()
        self.assertEqual(code, 1)
        self.assertIn("POSTGRES_USER: MISSING", output)
        self.assertIn("VW-CHECK: FAIL", output)


if __name__ == "__main__":
    unittest.main(verbosity=2)
