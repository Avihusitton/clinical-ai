# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from clinical_context_quarantine_package import (
    build_context_quarantine_package,
)
from context_quarantine_load_planner import (
    build_context_quarantine_plan,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
D4_PACKAGE = (
    Path(r"C:\Avihusitton\dherech-dictionery")
    / "Derech_Dictionary_Project"
    / "07_UPDATED_DICTIONARY"
    / "D4_CANONICAL_RELEASE"
)
DICTIONARY_PLAN = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "d4_canonical_preflight"
    / "dictionary_graph_plan"
)


@unittest.skipUnless(
    D4_PACKAGE.is_dir() and DICTIONARY_PLAN.is_dir(),
    "canonical D4 artifacts unavailable",
)
class ContextQuarantinePackageTests(unittest.TestCase):
    def test_package_and_plan_preserve_quarantine(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package_dir = root / "package"
            package = build_context_quarantine_package(
                REPO_ROOT
                / "data"
                / "concept_relationships_queue.json",
                D4_PACKAGE
                / "CLINICAL_AI_CONTEXT_RELATION_PROVENANCE.jsonl",
                package_dir,
                "D4-99F53565A7BCC45E",
            )
            self.assertEqual(
                package["status"],
                "PASS_CONTEXT_QUARANTINE_PACKAGE_CREATED",
            )
            self.assertEqual(
                package["counts"]["relation_candidates"],
                32,
            )
            self.assertEqual(
                package["counts"]["both_endpoints_unique"],
                9,
            )
            self.assertEqual(package["automatic_promotions"], 0)

            plan_dir = root / "plan"
            plan = build_context_quarantine_plan(
                package_dir,
                DICTIONARY_PLAN,
                plan_dir,
            )
            self.assertEqual(
                plan["status"],
                "PASS_WRITE_FREE_CONTEXT_QUARANTINE_PLAN",
            )
            self.assertEqual(
                plan["counts"]["canonical_semantic_edges"],
                0,
            )
            self.assertTrue(
                plan["eligible_for_staging_quarantine_load"]
            )
            edges = [
                json.loads(line)
                for line in (
                    plan_dir / "context_quarantine_edges.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            self.assertTrue(
                all(
                    row["relation_type"]
                    in {
                        "SUPPORTED_BY_EXCERPT",
                        "CANDIDATE_SOURCE_ENDPOINT",
                        "CANDIDATE_TARGET_ENDPOINT",
                    }
                    for row in edges
                )
            )


if __name__ == "__main__":
    unittest.main()
