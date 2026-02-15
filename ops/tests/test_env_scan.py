#!/usr/bin/env python3
"""Unit tests for env_scan utilities."""

from __future__ import annotations

import importlib.util
import os
import pathlib
import unittest
from unittest import mock


REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


def load_env_scan_module():
    module_path = REPO_ROOT / "ops" / "bin" / "env_scan.py"
    spec = importlib.util.spec_from_file_location("env_scan_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load env_scan module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class EnvScanTests(unittest.TestCase):
    def test_extract_vars_supports_default_pattern(self) -> None:
        module = load_env_scan_module()
        text = "A=${VAR_A} B=${VAR_B:-default} C=${VAR_C:-x-y}"
        self.assertEqual(module.extract_vars_from_text(text), ["VAR_A", "VAR_B", "VAR_C"])

    def test_manifest_render_is_deterministic(self) -> None:
        module = load_env_scan_module()
        scan = {
            "core": {"POSTGRES_PASSWORD": 2, "POSTGRES_DB": 1},
            "edge": {"PUBLIC_DOMAIN": 1, "TUNNEL_TOKEN": 1},
        }
        rendered_one = module.render_env_manifest(scan, ["POSTGRES_PASSWORD", "TUNNEL_TOKEN"])
        rendered_two = module.render_env_manifest(scan, ["POSTGRES_PASSWORD", "TUNNEL_TOKEN"])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("| `POSTGRES_PASSWORD` | 2 | yes | yes |", rendered_one)
        self.assertIn("| `PUBLIC_DOMAIN` | 1 | no | no |", rendered_one)

    @mock.patch.dict(
        os.environ,
        {
            "PUBLIC_DOMAIN": "thecortexstack.com",
            "POSTGRES_PASSWORD": "super-secret-value",
        },
        clear=False,
    )
    def test_env_check_explain_includes_counts_without_values(self) -> None:
        module = load_env_scan_module()
        fake_scan = {
            "core": {"PUBLIC_DOMAIN": 0, "POSTGRES_PASSWORD": 1},
            "edge": {"PUBLIC_DOMAIN": 1, "POSTGRES_PASSWORD": 0},
        }
        with mock.patch.object(module, "scan_compose_env_vars", return_value=fake_scan):
            lines, failed = module.env_check_lines(explain=True)
        self.assertTrue(any("PUBLIC_DOMAIN: OK — core:0 edge:1" in line for line in lines))
        self.assertTrue(any("POSTGRES_PASSWORD: OK — core:1 edge:0" in line for line in lines))
        self.assertFalse(any("super-secret-value" in line for line in lines))
        self.assertTrue(failed)
        self.assertEqual(lines[-1], "ENV-CHECK: FAIL")


if __name__ == "__main__":
    unittest.main(verbosity=2)
