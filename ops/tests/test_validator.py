#!/usr/bin/env python3
"""Unit tests for repository validator rules."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def load_validator_module():
    module_path = REPO_ROOT / "ops" / "validator" / "validate_repo.py"
    spec = importlib.util.spec_from_file_location("validate_repo_for_tests", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("failed to load validator module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidatorComposeTagTests(unittest.TestCase):
    def test_compose_latest_tag_is_rejected(self) -> None:
        module = load_validator_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            compose_rel = "bootstrap/compose/temp/docker-compose.yml"
            compose_path = repo_root / compose_rel
            compose_path.parent.mkdir(parents=True, exist_ok=True)
            compose_path.write_text(
                "services:\n  app:\n    image: example/app:latest\n",
                encoding="utf-8",
            )

            hits = module.check_compose_latest_tags(repo_root, [compose_rel])

        self.assertEqual(len(hits), 1)
        self.assertIn(compose_rel, hits[0])
        self.assertIn("example/app:latest", hits[0])

    def test_compose_pinned_tag_is_allowed(self) -> None:
        module = load_validator_module()
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            compose_rel = "bootstrap/compose/temp/docker-compose.yml"
            compose_path = repo_root / compose_rel
            compose_path.parent.mkdir(parents=True, exist_ok=True)
            compose_path.write_text(
                "services:\n  app:\n    image: example/app:1.2.3\n",
                encoding="utf-8",
            )

            hits = module.check_compose_latest_tags(repo_root, [compose_rel])

        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
