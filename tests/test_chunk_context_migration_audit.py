# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from chunk_context_migration_audit import (
    _build_alias_index,
    _map_term,
    create_chunk_context_audit,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_DIR = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "dictionary_preview_graph_plan"
)


@unittest.skipUnless(PLAN_DIR.is_dir(), "preview graph plan unavailable")
class ChunkContextMigrationAuditTests(unittest.TestCase):
    def test_hebrew_diacritics_do_not_change_identity_match(self) -> None:
        alias_index = {"פגיעות": {"B035"}}
        self.assertEqual(
            _map_term("פגיעוּת", alias_index),
            ("UNIQUE", ["B035"]),
        )

    def test_redirect_alias_maps_to_active_target(self) -> None:
        nodes = [
            {
                "node_key": "GlossaryEntry:A001",
                "labels": ["GlossaryEntry"],
                "properties": {
                    "card_id": "A001",
                    "status": "APPROVED",
                    "entry_name": "מושג פעיל",
                    "aliases_and_spellings": [],
                },
            },
            {
                "node_key": "GlossaryEntry:B001",
                "labels": ["GlossaryEntry", "DictionaryRedirect"],
                "properties": {
                    "card_id": "B001",
                    "status": "DEPRECATED",
                    "entry_name": "שם היסטורי",
                    "aliases_and_spellings": ["כינוי היסטורי"],
                },
            },
        ]
        edges = [
            {
                "source_node_key": "GlossaryEntry:B001",
                "target_node_key": "GlossaryEntry:A001",
                "relation_type": "REDIRECTS_TO",
            }
        ]
        alias_index, active_ids = _build_alias_index(nodes, edges)
        self.assertEqual(active_ids, {"A001"})
        self.assertEqual(
            _map_term("כינוי היסטורי", alias_index),
            ("UNIQUE", ["A001"]),
        )

    def test_existing_context_is_quarantined_and_write_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            report = create_chunk_context_audit(
                PLAN_DIR,
                REPO_ROOT / "data" / "concept_relationships_queue.json",
                REPO_ROOT / "out" / "neo4j_baseline_stats.json",
                REPO_ROOT / "out" / "linking_stats.json",
                REPO_ROOT / "out" / "manifest.json",
                Path(temporary),
            )
            self.assertEqual(
                report["status"],
                "PASS_WRITE_FREE_CHUNK_CONTEXT_AUDIT",
            )
            self.assertEqual(
                report["legacy_inventory"][
                    "queued_relation_candidates"
                ],
                32,
            )
            self.assertEqual(
                report["mapping"]["automatically_promoted"],
                0,
            )
            self.assertEqual(
                report["controls"]["neo4j_connections"],
                0,
            )
            self.assertEqual(report["controls"]["neo4j_writes"], 0)
            self.assertFalse(report["eligible_for_chunk_context_load"])

    def test_generated_candidates_do_not_copy_quotes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary)
            report = create_chunk_context_audit(
                PLAN_DIR,
                REPO_ROOT / "data" / "concept_relationships_queue.json",
                REPO_ROOT / "out" / "neo4j_baseline_stats.json",
                REPO_ROOT / "out" / "linking_stats.json",
                REPO_ROOT / "out" / "manifest.json",
                output_dir,
            )
            rows = [
                json.loads(line)
                for line in Path(
                    report["candidate_artifact"]["path"]
                ).read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(rows), 32)
            self.assertTrue(
                all("quote" not in row for row in rows)
            )
            self.assertTrue(
                all(
                    row["eligible_for_load"] is False
                    for row in rows
                )
            )

    def test_report_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first_dir = Path(temporary) / "first"
            second_dir = Path(temporary) / "second"
            create_chunk_context_audit(
                PLAN_DIR,
                REPO_ROOT / "data" / "concept_relationships_queue.json",
                REPO_ROOT / "out" / "neo4j_baseline_stats.json",
                REPO_ROOT / "out" / "linking_stats.json",
                REPO_ROOT / "out" / "manifest.json",
                first_dir,
            )
            create_chunk_context_audit(
                PLAN_DIR,
                REPO_ROOT / "data" / "concept_relationships_queue.json",
                REPO_ROOT / "out" / "neo4j_baseline_stats.json",
                REPO_ROOT / "out" / "linking_stats.json",
                REPO_ROOT / "out" / "manifest.json",
                second_dir,
            )
            first_report = next(
                first_dir.glob("chunk_context_migration_audit*.json")
            )
            second_report = next(
                second_dir.glob("chunk_context_migration_audit*.json")
            )
            first = json.loads(first_report.read_text(encoding="utf-8"))
            second = json.loads(
                second_report.read_text(encoding="utf-8")
            )
            first["candidate_artifact"].pop("path")
            second["candidate_artifact"].pop("path")
            self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
