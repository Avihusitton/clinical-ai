# -*- coding: utf-8 -*-

from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from canonical_context_quarantine_staging_loader import (
    inspect_readiness,
    load_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "d4_canonical_preflight"
    / "context_quarantine_graph_plan"
)


@unittest.skipUnless(PLAN_DIR.is_dir(), "quarantine plan unavailable")
class CanonicalContextQuarantineStagingLoaderTests(unittest.TestCase):
    def test_plan_is_verified_and_contains_no_semantic_edges(self) -> None:
        plan = load_plan(PLAN_DIR)
        self.assertEqual(len(plan["nodes"]), 52)
        self.assertEqual(len(plan["edges"]), 73)
        self.assertEqual(
            plan["manifest"]["counts"]["canonical_semantic_edges"],
            0,
        )

    def test_matching_dictionary_evidence_passes_local_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            evidence_path = Path(temporary) / "dictionary_evidence.json"
            evidence_path.write_text(
                json.dumps(
                    {
                        "status": (
                            "PASS_CANONICAL_DICTIONARY_LOADED_TO_STAGING"
                        ),
                        "source_release_id": "D4-99F53565A7BCC45E",
                        "ingestion_batch_id": "DICTBATCH-TEST",
                        "post_load_validation": {
                            "status": "PASS_POST_LOAD_VALIDATION"
                        },
                    }
                ),
                encoding="utf-8",
            )
            report = inspect_readiness(
                PLAN_DIR,
                evidence_path,
                REPO_ROOT / ".env",
            )
            self.assertEqual(
                report["status"],
                "PASS_CONTEXT_QUARANTINE_EXECUTION_GATES",
            )
            self.assertEqual(report["neo4j_connections"], 0)
            self.assertEqual(report["neo4j_writes"], 0)
            self.assertFalse(report["neo4j_driver_imported"])

    def test_neo4j_is_not_imported_at_module_scope(self) -> None:
        source = (
            REPO_ROOT
            / "canonical_context_quarantine_staging_loader.py"
        ).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = [
            alias.name
            for node in tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        ]
        self.assertNotIn("neo4j", imports)


if __name__ == "__main__":
    unittest.main()
