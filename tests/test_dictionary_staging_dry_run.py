# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dictionary_staging_dry_run import (
    DryRunRejected,
    _identifier_findings,
    create_staging_dry_run,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "dictionary_preview_graph_plan"
)


@unittest.skipUnless(PLAN_DIR.is_dir(), "preview graph plan unavailable")
class DictionaryStagingDryRunTests(unittest.TestCase):
    def test_preview_dry_run_is_clean_and_write_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dry_run.json"
            report = create_staging_dry_run(PLAN_DIR, output)
            self.assertEqual(
                report["status"],
                "PASS_WRITE_FREE_STAGING_DRY_RUN",
            )
            self.assertEqual(report["counts"]["dry_run_errors"], 0)
            self.assertEqual(report["counts"]["records_rejected"], 0)
            self.assertEqual(
                report["execution_controls"]["neo4j_connections"],
                0,
            )
            self.assertEqual(
                report["execution_controls"]["neo4j_writes"],
                0,
            )
            self.assertFalse(report["eligible_for_staging_execution"])
            self.assertIn(
                "CANONICAL_RELEASE_REQUIRED",
                report["blockers_for_staging_execution"],
            )

    def test_report_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first = Path(temporary) / "first.json"
            second = Path(temporary) / "second.json"
            create_staging_dry_run(PLAN_DIR, first)
            create_staging_dry_run(PLAN_DIR, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())

    def test_tampered_artifact_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copied = Path(temporary) / "plan"
            shutil.copytree(PLAN_DIR, copied)
            nodes = next(copied.glob("dictionary_nodes*.jsonl"))
            nodes.write_bytes(nodes.read_bytes() + b"\n")
            with self.assertRaises(DryRunRejected):
                create_staging_dry_run(
                    copied,
                    Path(temporary) / "out.json",
                )

    def test_candidates_are_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "dry_run.json"
            report = create_staging_dry_run(PLAN_DIR, output)
            self.assertEqual(
                report["counts"]["relation_candidates_quarantined"],
                2,
            )
            self.assertEqual(
                report["execution_controls"][
                    "candidate_edges_in_load_plan"
                ],
                0,
            )
            saved = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(saved, report)

    def test_structured_source_id_is_not_mistaken_for_personal_id(
        self,
    ) -> None:
        nodes = [
            {
                "labels": ["GlossaryEntry"],
                "identity_value": "A001",
                "properties": {
                    "exact_source": (
                        "paragraph:12; SRC-FEFE12D123456789"
                    )
                },
            }
        ]
        self.assertEqual(_identifier_findings(nodes), [])

    def test_real_nine_digit_candidate_is_still_blocked(self) -> None:
        nodes = [
            {
                "labels": ["GlossaryEntry"],
                "identity_value": "A001",
                "properties": {
                    "short_example": "מזהה 123456782"
                },
            }
        ]
        self.assertEqual(
            _identifier_findings(nodes),
            ["A001:israeli_id_candidate"],
        )


if __name__ == "__main__":
    unittest.main()
