# -*- coding: utf-8 -*-

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from dictionary_release_adapter import build_graph_plan


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "data" / "official_glossary" / "schema.json"
PREVIEW_PATH = Path(
    r"C:\Avihusitton\dherech-dictionery\Derech_Dictionary_Project"
    r"\07_UPDATED_DICTIONARY\CLINICAL_AI_PREVIEW"
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@unittest.skipUnless(PREVIEW_PATH.is_dir(), "dictionary preview is unavailable")
class DictionaryReleaseAdapterTests(unittest.TestCase):
    def test_preview_builds_write_free_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "plan"
            report = build_graph_plan(
                PREVIEW_PATH,
                SCHEMA_PATH,
                output_dir,
            )
            self.assertEqual(
                report["status"],
                "PASS_WRITE_FREE_GRAPH_PLAN_CREATED",
            )
            self.assertEqual(report["neo4j_connections"], 0)
            self.assertEqual(report["neo4j_writes"], 0)
            self.assertFalse(report["eligible_for_neo4j_write"])
            self.assertEqual(report["counts"]["glossary_nodes"], 17)
            self.assertEqual(report["counts"]["redirect_edges"], 1)
            self.assertEqual(
                report["counts"]["approved_dictionary_edges"], 15
            )
            self.assertEqual(report["counts"]["relation_candidates"], 2)

    def test_all_edges_resolve_to_plan_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "plan"
            build_graph_plan(PREVIEW_PATH, SCHEMA_PATH, output_dir)
            nodes = [
                json.loads(line)
                for line in (
                    output_dir / "dictionary_nodes.preview.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            edges = [
                json.loads(line)
                for line in (
                    output_dir / "dictionary_edges.preview.jsonl"
                ).read_text(encoding="utf-8").splitlines()
            ]
            node_keys = {node["node_key"] for node in nodes}
            for edge in edges:
                self.assertIn(edge["source_node_key"], node_keys)
                self.assertIn(edge["target_node_key"], node_keys)

    def test_candidates_are_not_load_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            output_dir = Path(temporary) / "plan"
            build_graph_plan(PREVIEW_PATH, SCHEMA_PATH, output_dir)
            edges = (
                output_dir / "dictionary_edges.preview.jsonl"
            ).read_text(encoding="utf-8")
            candidates = (
                output_dir
                / "dictionary_relation_candidates.preview.jsonl"
            ).read_text(encoding="utf-8")
            self.assertNotIn("PENDING_DICTIONARY_REVIEW", edges)
            self.assertIn("PENDING_DICTIONARY_REVIEW", candidates)

    def test_plan_is_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            first_dir = Path(temporary) / "first"
            second_dir = Path(temporary) / "second"
            first = build_graph_plan(
                PREVIEW_PATH,
                SCHEMA_PATH,
                first_dir,
            )
            second = build_graph_plan(
                PREVIEW_PATH,
                SCHEMA_PATH,
                second_dir,
            )
            self.assertEqual(first["plan_id"], second["plan_id"])
            for filename in (
                "dictionary_nodes.preview.jsonl",
                "dictionary_edges.preview.jsonl",
                "dictionary_relation_candidates.preview.jsonl",
                "dictionary_graph_plan_manifest.preview.json",
            ):
                self.assertEqual(
                    file_hash(first_dir / filename),
                    file_hash(second_dir / filename),
                )


if __name__ == "__main__":
    unittest.main()
