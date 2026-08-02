# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from unified_release_preflight import run_unified_preflight


REPO_ROOT = Path(__file__).resolve().parents[1]
PREVIEW_PATH = Path(
    r"C:\Avihusitton\dherech-dictionery\Derech_Dictionary_Project"
    r"\07_UPDATED_DICTIONARY\CLINICAL_AI_PREVIEW"
)


@unittest.skipUnless(PREVIEW_PATH.is_dir(), "dictionary preview unavailable")
class UnifiedReleasePreflightTests(unittest.TestCase):
    def test_preview_completes_all_zero_write_stages(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = run_unified_preflight(
                PREVIEW_PATH,
                REPO_ROOT / "data" / "official_glossary" / "schema.json",
                REPO_ROOT / "data" / "concept_relationships_queue.json",
                REPO_ROOT / "out" / "neo4j_baseline_stats.json",
                REPO_ROOT / "out" / "linking_stats.json",
                REPO_ROOT / "out" / "manifest.json",
                Path(temporary),
            )
            self.assertEqual(
                report["status"],
                "PASS_PREVIEW_PROOF_NOT_LOADABLE",
            )
            self.assertEqual(report["counts"]["dry_run_errors"], 0)
            self.assertEqual(report["counts"]["records_rejected"], 0)
            self.assertEqual(report["neo4j_connections"], 0)
            self.assertEqual(report["neo4j_writes"], 0)
            self.assertFalse(
                report["eligible_for_staging_target_verification"]
            )

    def test_summary_and_all_stage_artifacts_are_created(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_root = Path(temporary)
            report = run_unified_preflight(
                PREVIEW_PATH,
                REPO_ROOT / "data" / "official_glossary" / "schema.json",
                REPO_ROOT / "data" / "concept_relationships_queue.json",
                REPO_ROOT / "out" / "neo4j_baseline_stats.json",
                REPO_ROOT / "out" / "linking_stats.json",
                REPO_ROOT / "out" / "manifest.json",
                output_root,
            )
            summary = json.loads(
                (
                    output_root / "unified_preflight_summary.json"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(summary, report)
            for path in report["artifacts"].values():
                self.assertTrue(Path(path).is_file())


if __name__ == "__main__":
    unittest.main()
