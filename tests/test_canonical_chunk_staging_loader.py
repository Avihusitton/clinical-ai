# -*- coding: utf-8 -*-

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from canonical_chunk_staging_loader import (
    load_chunk_plan,
    validate_chunk_execution_gates,
)
from chunk_context_load_planner import build_chunk_context_plan
from tests.test_chunk_release_and_plan import _make_chunk_package


REPO_ROOT = Path(__file__).resolve().parents[1]
DICTIONARY_PLAN = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "dictionary_preview_graph_plan"
)


@unittest.skipUnless(
    DICTIONARY_PLAN.is_dir(),
    "dictionary graph plan unavailable",
)
class CanonicalChunkStagingLoaderTests(unittest.TestCase):
    def _make_plan(self, root: Path) -> Path:
        package = _make_chunk_package(root)
        plan_dir = root / "chunk_plan"
        build_chunk_context_plan(
            package,
            DICTIONARY_PLAN,
            plan_dir,
        )
        return plan_dir

    def test_chunk_plan_is_independently_verified(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plan = load_chunk_plan(
                self._make_plan(Path(temporary))
            )
            self.assertEqual(len(plan["nodes"]), 1)
            self.assertEqual(len(plan["edges"]), 1)
            self.assertEqual(
                plan["manifest"]["dictionary_release_id"],
                "RELEASE-TEST",
            )

    def test_dictionary_first_gate_can_pass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plan = load_chunk_plan(
                self._make_plan(Path(temporary))
            )
            dictionary_evidence = {
                "status": (
                    "PASS_CANONICAL_DICTIONARY_LOADED_TO_STAGING"
                ),
                "source_release_id": "RELEASE-TEST",
                "post_load_validation": {
                    "status": "PASS_POST_LOAD_VALIDATION"
                },
            }
            target = {
                "status": (
                    "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
                ),
                "eligible_for_readonly_runtime_verification": True,
            }
            report = validate_chunk_execution_gates(
                plan,
                dictionary_evidence,
                target,
            )
            self.assertEqual(
                report["status"],
                "PASS_CHUNK_EXECUTION_GATES",
            )
            self.assertTrue(report["eligible_for_staging_execution"])

    def test_missing_dictionary_load_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plan = load_chunk_plan(
                self._make_plan(Path(temporary))
            )
            report = validate_chunk_execution_gates(
                plan,
                {},
                {
                    "status": (
                        "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
                    ),
                    "eligible_for_readonly_runtime_verification": True,
                },
            )
            self.assertIn(
                "DICTIONARY_STAGING_LOAD_REQUIRED",
                report["blockers"],
            )
            self.assertFalse(report["eligible_for_staging_execution"])

    def test_pending_context_queue_is_never_in_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            plan_dir = self._make_plan(Path(temporary))
            manifest = json.loads(
                (
                    plan_dir / "chunk_graph_plan_manifest.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                manifest["controls"]["pending_context_queue_included"],
                0,
            )

    def test_neo4j_is_not_imported_at_module_scope(self) -> None:
        source = (
            REPO_ROOT / "canonical_chunk_staging_loader.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [
            node
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        imported_names = {
            alias.name
            for node in imports
            for alias in node.names
        }
        self.assertNotIn("neo4j", imported_names)


if __name__ == "__main__":
    unittest.main()
