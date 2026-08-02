# -*- coding: utf-8 -*-

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path

from canonical_dictionary_staging_loader import (
    CONSTRAINTS,
    StagingLoadBlocked,
    inspect_execution_readiness,
    load_plan,
    validate_execution_gates,
    verify_runtime_target,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "dictionary_preview_graph_plan"
)
PREFLIGHT_SUMMARY = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "unified_preview_preflight"
    / "unified_preflight_summary.json"
)


@unittest.skipUnless(PLAN_DIR.is_dir(), "preview plan unavailable")
class CanonicalDictionaryStagingLoaderTests(unittest.TestCase):
    def test_preview_is_blocked_before_any_connection(self) -> None:
        report = inspect_execution_readiness(
            PLAN_DIR,
            PREFLIGHT_SUMMARY,
            REPO_ROOT / ".env",
        )
        self.assertEqual(report["status"], "BLOCKED_EXECUTION_GATES")
        self.assertIn("PREVIEW_PLAN_FORBIDDEN", report["blockers"])
        self.assertEqual(report["neo4j_connections"], 0)
        self.assertEqual(report["neo4j_writes"], 0)
        self.assertFalse(report["neo4j_driver_imported"])

    def test_plan_is_independently_verified(self) -> None:
        plan = load_plan(PLAN_DIR)
        self.assertEqual(len(plan["nodes"]), 20)
        self.assertEqual(len(plan["edges"]), 33)
        self.assertEqual(len(plan["candidates"]), 2)

    def test_canonical_gate_contract_can_pass(self) -> None:
        plan = load_plan(PLAN_DIR)
        plan["manifest"]["preview"] = False
        plan["manifest"]["source_manifest_status"] = (
            "D4_CANONICAL_RELEASE"
        )
        preflight = {
            "status": (
                "PASS_CANONICAL_READY_FOR_STAGING_TARGET_PREFLIGHT"
            ),
            "eligible_for_staging_target_verification": True,
            "neo4j_writes": 0,
        }
        target = {
            "status": (
                "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
            ),
            "eligible_for_readonly_runtime_verification": True,
        }
        report = validate_execution_gates(
            plan,
            preflight,
            target,
        )
        self.assertEqual(report["status"], "PASS_EXECUTION_GATES")
        self.assertTrue(report["eligible_for_staging_execution"])
        self.assertFalse(report["eligible_for_production_execution"])

    def test_neo4j_is_not_imported_at_module_scope(self) -> None:
        source_path = (
            REPO_ROOT / "canonical_dictionary_staging_loader.py"
        )
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
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

    def test_preview_summary_is_zero_write(self) -> None:
        summary = json.loads(
            PREFLIGHT_SUMMARY.read_text(encoding="utf-8")
        )
        self.assertEqual(summary["neo4j_writes"], 0)
        self.assertFalse(
            summary["eligible_for_staging_target_verification"]
        )

    def test_rollback_contract_keeps_schema_constraints(self) -> None:
        constraint_names = [name for name, _ in CONSTRAINTS]
        self.assertEqual(
            constraint_names,
            [
                "dictionary_entity_node_key_unique",
                "glossaryentry_card_id_unique",
                "source_document_id_unique",
            ],
        )

    def test_preview_blocks_runtime_connection(self) -> None:
        calls = []

        def forbidden_driver_factory(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("driver must not be opened")

        with self.assertRaises(StagingLoadBlocked) as context:
            verify_runtime_target(
                PLAN_DIR,
                PREFLIGHT_SUMMARY,
                REPO_ROOT / ".env",
                REPO_ROOT
                / "out"
                / "unified_program"
                / "test_runtime_evidence.json",
                driver_factory=forbidden_driver_factory,
            )
        self.assertIn(
            "PREVIEW_PLAN_FORBIDDEN",
            str(context.exception),
        )
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
