#!/usr/bin/env python3
"""Unit tests for project manifest validation and catalog rendering."""

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


def load_project_manifest_module():
    module_path = REPO_ROOT / "ops" / "bin" / "project_manifest.py"
    spec = importlib.util.spec_from_file_location("project_manifest_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load project_manifest module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ProjectManifestTests(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_project_manifest_module()
        self.sample = {
            "schema_version": 1,
            "project": {"key": "sample-app", "name": "Sample App", "environment": "dev"},
            "targets": {
                "runtime_host": "sample-app-dev",
                "ingress_host": "cortex-control",
                "data_host": "cortex-data",
            },
            "domains": {"public": ["app.example.test", "api.example.test"]},
            "services": {
                "frontend": {"type": "nextjs", "enabled": True},
                "backend": {"type": "fastapi", "enabled": True},
                "postgres": {"type": "postgres", "enabled": True, "shared": True, "extensions": ["pgvector"]},
            },
            "routes": [
                {"host": "app.example.test", "service": "frontend", "port": 3000},
                {"host": "api.example.test", "service": "backend", "port": 8000},
            ],
            "secrets": {"vaultwarden_items": ["sample-app-runtime", "sample-app-db"]},
        }

    def test_validate_manifest_payload_accepts_valid_manifest(self) -> None:
        errors = self.module.validate_manifest_payload(Path("projects/sample.json"), self.sample)
        self.assertEqual(errors, [])

    def test_validate_manifest_payload_rejects_route_to_disabled_service(self) -> None:
        payload = json.loads(json.dumps(self.sample))
        payload["services"]["backend"]["enabled"] = False
        errors = self.module.validate_manifest_payload(Path("projects/sample.json"), payload)
        self.assertTrue(any("route service `backend` is not enabled" in item for item in errors))

    def test_render_catalog_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_catalog([manifest])
        rendered_two = self.module.render_catalog([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Edit manifests in `projects/` and rerun `make project-catalog`", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` |", rendered_one)
        self.assertIn("`frontend (nextjs)`", rendered_one)

    def test_render_caddy_route_preview_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        manifest["routes"] = list(reversed(manifest["routes"]))
        rendered_one = self.module.render_caddy_route_preview([manifest])
        rendered_two = self.module.render_caddy_route_preview([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("# Preview only. This file does not change live routing.", rendered_one)
        self.assertIn("api.example.test {\n\t# service: backend (fastapi)\n\treverse_proxy sample-app-dev:8000\n}", rendered_one)
        self.assertLess(rendered_one.index("api.example.test {"), rendered_one.index("app.example.test {"))

    def test_render_caddy_route_preview_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_caddy_route_preview([manifest_one, manifest_two])

    def test_render_deploy_plan_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_deploy_plan([manifest])
        rendered_two = self.module.render_deploy_plan([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Planning only. This artifact does not provision hosts, deploy services, or change live routing.", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | `cortex-control` | `cortex-data` |", rendered_one)
        self.assertIn("| `backend` | `fastapi` | `no` | `<none>` |", rendered_one)
        self.assertIn("| `postgres` | `postgres` | `yes` | extensions: `pgvector` |", rendered_one)
        self.assertIn("| `app.example.test` | `frontend` | 3000 | `sample-app-dev:3000` |", rendered_one)
        self.assertIn("- `sample-app-db`", rendered_one)
        self.assertIn("- [ ] Confirm target hosts are ready: runtime `sample-app-dev`, ingress `cortex-control`, data `cortex-data`.", rendered_one)

    def test_render_deploy_plan_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_deploy_plan([manifest_one, manifest_two])

    def test_render_bootstrap_checklist_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_bootstrap_checklist([manifest])
        rendered_two = self.module.render_bootstrap_checklist([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Planning only. This artifact does not bootstrap hosts, create compose files, or change live routing.", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | 2 | 1 | 2 | 2 |", rendered_one)
        self.assertIn("| `postgres` | `postgres` | `yes` | `shared dependency` | extensions: `pgvector` |", rendered_one)
        self.assertIn("| `app.example.test` | `frontend` | 3000 | `cortex-control -> sample-app-dev:3000` |", rendered_one)
        self.assertIn("- [ ] Approve `sample-app-dev` as the first single-VM runtime host for `sample-app`.", rendered_one)

    def test_render_bootstrap_checklist_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_bootstrap_checklist([manifest_one, manifest_two])

    def test_render_runtime_skeleton_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_runtime_skeleton([manifest])
        rendered_two = self.module.render_runtime_skeleton([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Planning only. This artifact does not create compose bundles, deploy containers, or change live routing.", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | 2 | 1 | 2 |", rendered_one)
        self.assertIn("| `frontend` | `nextjs` | `3000` | `postgres` |", rendered_one)
        self.assertIn("| `postgres` | `postgres` | `cortex-data` | extensions: `pgvector` |", rendered_one)
        self.assertIn("image: ghcr.io/example/sample-app/frontend:dev", rendered_one)
        self.assertIn("POSTGRES_ATTACHMENT: from-cortex-data", rendered_one)

    def test_render_runtime_skeleton_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_runtime_skeleton([manifest_one, manifest_two])

    def test_render_env_contract_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_env_contract([manifest])
        rendered_two = self.module.render_env_contract([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Planning only. This artifact does not resolve Vaultwarden items, inject env values, or deploy services.", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | 2 | 1 | 2 |", rendered_one)
        self.assertIn("| `postgres` | `postgres` | `POSTGRES_ATTACHMENT` | `POSTGRES_HOST`, `POSTGRES_PORT` | `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `DATABASE_URL` | `sample-app-db`, `sample-app-runtime` |", rendered_one)
        self.assertIn("| `backend` | `fastapi` | `PROJECT_KEY`, `PROJECT_ENV`, `PORT`, `PUBLIC_ROUTE_HOSTS`, `POSTGRES_ATTACHMENT` | `POSTGRES_ATTACHMENT` | manual retrieval for `sample-app-db`, `sample-app-runtime` |", rendered_one)

    def test_render_env_contract_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_env_contract([manifest_one, manifest_two])

    def test_render_smoke_check_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_smoke_check([manifest])
        rendered_two = self.module.render_smoke_check([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Planning only. This artifact does not execute live health checks, hit live routes, or change deployment state.", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | 2 | 1 | 2 | 4 |", rendered_one)
        self.assertIn("| `frontend` | `nextjs` | `3000` | Confirm `frontend` is visible on `sample-app-dev` and listening on `3000`. |", rendered_one)
        self.assertIn("| `app.example.test` | `frontend` | 3000 | `sample-app-dev:3000` |", rendered_one)
        self.assertIn("| `postgres` | `postgres` | `cortex-data` | Confirm `postgres` remains reachable from `sample-app-dev` on `cortex-data`. Required platform notes: `pgvector`. |", rendered_one)
        self.assertIn("- [ ] Routes: Confirm ingress `cortex-control` presents the documented public routes after deployment:", rendered_one)

    def test_render_smoke_check_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_smoke_check([manifest_one, manifest_two])

    def test_render_handoff_packet_is_deterministic(self) -> None:
        manifest = json.loads(json.dumps(self.sample))
        manifest["_path"] = "projects/examples/sample-app.json"
        rendered_one = self.module.render_handoff_packet([manifest])
        rendered_two = self.module.render_handoff_packet([manifest])
        self.assertEqual(rendered_one, rendered_two)
        self.assertIn("Planning only. This artifact does not bootstrap hosts, deploy services, resolve secret values, or execute health checks.", rendered_one)
        self.assertIn("| `sample-app` | `dev` | `sample-app-dev` | 2 | 2 | 1 | 2 |", rendered_one)
        self.assertIn("| Route preview | `docs/runbooks/generated/project-route-preview.md` | 2 route(s):", rendered_one)
        self.assertIn("| Env contract | `docs/runbooks/generated/project-env-contract.md` | 2 runtime contract(s), 1 shared dependency contract(s), attachment vars `POSTGRES_ATTACHMENT`, secret env vars `DATABASE_URL`, `POSTGRES_DB`, `POSTGRES_PASSWORD`, `POSTGRES_USER`. |", rendered_one)
        self.assertIn("- [ ] Review runtime skeleton and env contract together so attachment placeholders stay aligned: `POSTGRES_ATTACHMENT`.", rendered_one)

    def test_render_handoff_packet_rejects_duplicate_host_across_manifests(self) -> None:
        manifest_one = json.loads(json.dumps(self.sample))
        manifest_one["_path"] = "projects/examples/sample-app.json"
        manifest_two = json.loads(json.dumps(self.sample))
        manifest_two["_path"] = "projects/examples/other-app.json"
        manifest_two["project"]["key"] = "other-app"
        manifest_two["project"]["name"] = "Other App"
        with self.assertRaisesRegex(ValueError, "duplicate route host `app.example.test` across manifests"):
            self.module.render_handoff_packet([manifest_one, manifest_two])

    def test_cmd_catalog_writes_output(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "projects.md"
                exit_code = self.module.cmd_catalog(projects_dir, output)
            self.assertEqual(exit_code, 0)
            self.assertTrue(output.is_file())
            self.assertIn("# Project Catalog", output.read_text(encoding="utf-8"))

    def test_cmd_route_preview_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-route-preview.md"
                exit_code = self.module.cmd_route_preview(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Route Preview", rendered)
            self.assertIn("```caddyfile", rendered)
            self.assertIn("reverse_proxy sample-app-dev:3000", rendered)

    def test_cmd_deploy_plan_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-deploy-plan.md"
                exit_code = self.module.cmd_deploy_plan(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Deployment Plan", rendered)
            self.assertIn("Planning only. This artifact does not provision hosts, deploy services, or change live routing.", rendered)
            self.assertIn("| `frontend` | `nextjs` | `no` | `<none>` |", rendered)

    def test_cmd_bootstrap_checklist_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-bootstrap-checklist.md"
                exit_code = self.module.cmd_bootstrap_checklist(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Bootstrap Checklist", rendered)
            self.assertIn("Planning only. This artifact does not bootstrap hosts, create compose files, or change live routing.", rendered)
            self.assertIn("| `backend` | `fastapi` | `no` | `runtime host` | `<none>` |", rendered)

    def test_cmd_runtime_skeleton_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-runtime-skeleton.md"
                exit_code = self.module.cmd_runtime_skeleton(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Runtime Skeleton", rendered)
            self.assertIn("Planning only. This artifact does not create compose bundles, deploy containers, or change live routing.", rendered)
            self.assertIn("image: ghcr.io/example/sample-app/backend:dev", rendered)

    def test_cmd_env_contract_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-env-contract.md"
                exit_code = self.module.cmd_env_contract(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Env Contract", rendered)
            self.assertIn("### Shared Dependency Contract", rendered)
            self.assertIn("`POSTGRES_ATTACHMENT`", rendered)

    def test_cmd_smoke_check_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-smoke-check.md"
                exit_code = self.module.cmd_smoke_check(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Smoke Check Contract", rendered)
            self.assertIn("### Operator-Visible Checks", rendered)
            self.assertIn("Planning only. This artifact does not execute live health checks, hit live routes, or change deployment state.", rendered)

    def test_cmd_handoff_packet_writes_generated_doc(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            docs_dir = root / "docs" / "runbooks" / "generated"
            projects_dir.mkdir(parents=True)
            docs_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            with mock.patch.object(self.module, "REPO_ROOT", root):
                output = docs_dir / "project-handoff-packet.md"
                exit_code = self.module.cmd_handoff_packet(projects_dir, output)
            self.assertEqual(exit_code, 0)
            rendered = output.read_text(encoding="utf-8")
            self.assertIn("# Project Handoff Packet", rendered)
            self.assertIn("### Artifact References", rendered)
            self.assertIn("docs/runbooks/generated/project-smoke-check.md", rendered)

    def test_cmd_route_preview_prints_caddyfile_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_route_preview(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project manifest Caddy route preview", rendered)
            self.assertIn("app.example.test {", rendered)
            self.assertIn("reverse_proxy sample-app-dev:3000", rendered)

    def test_cmd_deploy_plan_prints_markdown_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_deploy_plan(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project Deployment Plan", rendered)
            self.assertIn("### Operator Checkpoints", rendered)
            self.assertIn("- `sample-app-runtime`", rendered)

    def test_cmd_bootstrap_checklist_prints_markdown_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_bootstrap_checklist(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project Bootstrap Checklist", rendered)
            self.assertIn("### Human Approval Checkpoints", rendered)
            self.assertIn("- `sample-app-db`", rendered)

    def test_cmd_runtime_skeleton_prints_markdown_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_runtime_skeleton(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project Runtime Skeleton", rendered)
            self.assertIn("### Planning Skeleton", rendered)
            self.assertIn("route.host: api.example.test", rendered)

    def test_cmd_env_contract_prints_markdown_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_env_contract(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project Env Contract", rendered)
            self.assertIn("### Runtime Service Contract", rendered)
            self.assertIn("- `sample-app-runtime`", rendered)

    def test_cmd_smoke_check_prints_markdown_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_smoke_check(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project Smoke Check Contract", rendered)
            self.assertIn("### Routes To Verify", rendered)
            self.assertIn("- [ ] Runtime services: Confirm runtime host `sample-app-dev` shows the planned workloads running:", rendered)

    def test_cmd_handoff_packet_prints_markdown_to_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as tempdir:
            root = Path(tempdir)
            projects_dir = root / "projects"
            projects_dir.mkdir(parents=True)
            (projects_dir / "sample-app.json").write_text(json.dumps(self.sample) + "\n", encoding="utf-8")
            stdout = io.StringIO()
            with mock.patch.object(self.module, "REPO_ROOT", root):
                with redirect_stdout(stdout):
                    exit_code = self.module.cmd_handoff_packet(projects_dir, None)
            self.assertEqual(exit_code, 0)
            rendered = stdout.getvalue()
            self.assertIn("# Project Handoff Packet", rendered)
            self.assertIn("### Operator Handoff Checklist", rendered)
            self.assertIn("docs/runbooks/generated/project-route-preview.md", rendered)


if __name__ == "__main__":
    unittest.main(verbosity=2)
