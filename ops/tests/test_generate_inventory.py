#!/usr/bin/env python3
"""Unit tests for the Cortex Governor inventory generator."""

from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_inventory_module():
    module_path = REPO_ROOT / "ops" / "bin" / "generate_inventory.py"
    spec = importlib.util.spec_from_file_location("generate_inventory_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load inventory module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class GenerateInventoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_inventory_module()
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "ops" / "inventory").mkdir(parents=True)
        (self.root / "docs" / "runbooks").mkdir(parents=True)
        (self.root / "projects" / "examples").mkdir(parents=True)
        (self.root / "infra" / "proxmox" / "cortex-control").mkdir(parents=True)
        (self.root / "infra" / "proxmox" / "cortex-data").mkdir(parents=True)

        (self.root / "ops" / "inventory" / "host-catalog.json").write_text(
            json.dumps(
                {
                    "version": 1,
                    "hosts": [
                        {
                            "key": "majelis",
                            "address": "192.168.1.124",
                            "role": "operator and development workstation",
                            "management": "manual-bootstrap",
                            "notes": "Canonical development box.",
                        },
                        {
                            "key": "cortex-control",
                            "address": "192.168.1.103",
                            "role": "shared control plane",
                            "management": "opentofu-proxmox",
                            "iac_dir": "infra/proxmox/cortex-control",
                            "notes": "Control plane services.",
                        },
                        {
                            "key": "cortex-data",
                            "role": "shared stateful services host",
                            "management": "opentofu-proxmox",
                            "iac_dir": "infra/proxmox/cortex-data",
                            "notes": "Data services.",
                        },
                    ],
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "docs" / "runbooks" / "ports-registry.yaml").write_text(
            "\n".join(
                [
                    "version: 1",
                    "ports:",
                    "  - port: 8085",
                    "    proto: tcp",
                    "    service: cortex-wiki",
                    "    where: cortex-control",
                    "    notes: Hosted wiki",
                    "  - port: 3001",
                    "    proto: tcp",
                    "    service: uptime-kuma",
                    "    where: cortex-control",
                    "    notes: Dashboard",
                    "  - port: 8000",
                    "    proto: tcp",
                    "    service: docs-dev-server",
                    "    where: majelis",
                    "    notes: Local docs",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        (self.root / "projects" / "examples" / "sample.json").write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "project": {
                        "key": "sample-app",
                        "name": "Sample App",
                        "environment": "dev",
                    },
                    "targets": {
                        "runtime_host": "sample-app-dev",
                        "ingress_host": "cortex-control",
                        "data_host": "cortex-data",
                    },
                    "domains": {
                        "public": [
                            "app.sample-app.thecortexstack.com",
                        ]
                    },
                    "services": {
                        "frontend": {
                            "enabled": True,
                            "type": "nextjs",
                        }
                    },
                    "routes": [
                        {
                            "host": "app.sample-app.thecortexstack.com",
                            "service": "frontend",
                            "port": 3000,
                        }
                    ],
                    "secrets": {
                        "vaultwarden_items": ["item-1"],
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "infra" / "proxmox" / "cortex-control" / "terraform.tfstate").write_text(
            json.dumps(
                {
                    "outputs": {
                        "vm_name": {"value": "cortex-control"},
                        "vm_id": {"value": 220},
                    }
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (self.root / "infra" / "proxmox" / "cortex-data" / "variables.tf").write_text(
            '\n'.join(
                [
                    'variable "vm_id" {',
                    "  default = 221",
                    "}",
                    'variable "vm_name" {',
                    '  default = "cortex-data"',
                    "}",
                    "",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_render_inventory_includes_hosts_ports_and_routes(self) -> None:
        rendered = self.module.render_inventory(self.root, stamp="2026-03-18 00:30")

        self.assertIn("# Inventory", rendered)
        self.assertIn("Generated: 2026-03-18 00:30 (local)", rendered)
        self.assertIn("| `cortex-control` | shared control plane | `192.168.1.103` |", rendered)
        self.assertIn("| 8085 | `tcp` | `cortex-wiki` | Hosted wiki |", rendered)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | `cortex-control` | `cortex-data` |", rendered)
        self.assertIn("| `app.sample-app.thecortexstack.com` | `sample-app` | `dev` | `frontend` | 3000 |", rendered)
        self.assertIn("`http://cortex-control:8085` - hosted Governor wiki", rendered)
        self.assertIn("`https://app.sample-app.thecortexstack.com` - `sample-app` public route for `frontend`", rendered)
        self.assertIn("Host catalog: `ops/inventory/host-catalog.json`", rendered)

    def test_load_iac_facts_falls_back_to_variable_defaults(self) -> None:
        host = {
            "key": "cortex-data",
            "role": "shared stateful services host",
            "management": "opentofu-proxmox",
            "iac_dir": "infra/proxmox/cortex-data",
        }

        facts = self.module.load_iac_facts(self.root, host)

        self.assertEqual(facts["status"], "declared")
        self.assertEqual(facts["source"], "variables.tf")
        self.assertEqual(facts["vm_name"], "cortex-data")
        self.assertEqual(facts["vm_id"], 221)


if __name__ == "__main__":
    unittest.main(verbosity=2)
