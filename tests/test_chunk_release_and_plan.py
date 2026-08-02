# -*- coding: utf-8 -*-

from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from chunk_context_load_planner import (
    ChunkPlanRejected,
    build_chunk_context_plan,
)
from chunk_release_acceptance import validate_chunk_package
from dictionary_release_acceptance import sha256_file


REPO_ROOT = Path(__file__).resolve().parents[1]
DICTIONARY_PLAN = (
    REPO_ROOT
    / "out"
    / "unified_program"
    / "dictionary_preview_graph_plan"
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False) + "\n" for row in rows
        ),
        encoding="utf-8",
    )


def _make_chunk_package(root: Path, card_id: str = "A004") -> Path:
    package = root / "chunk_package"
    package.mkdir()
    text = "טקסט לימודי מנוטרל מזהים"
    chunk_id = hashlib.sha256(b"chunk").hexdigest()[:24]
    chunks = [
        {
            "chunk_id": chunk_id,
            "doc_id": "synthetic_doc",
            "source_document_id": "SRC-1234567890ABCDEF",
            "source_file_sha256": hashlib.sha256(b"source").hexdigest(),
            "text_sha256": hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest(),
            "deidentified_text": text,
            "paragraph_range": [0, 2],
            "lesson_number": None,
            "lesson_date": None,
            "temporal_status": "timeless",
            "modality": "general",
            "heading_path": ["בדיקה"],
            "source_authority": "METHOD_PRIMARY",
            "deidentification_status": "PASS",
            "data_classification": "SYNTHETIC",
        }
    ]
    relationships = [
        {
            "edge_id": "CHUNKEDGE-1234567890ABCDEF",
            "chunk_id": chunk_id,
            "card_id": card_id,
            "relation_type": "HAS_CANDIDATE",
            "review_status": "DETERMINISTIC_CANDIDATE",
            "verification_id": None,
            "dictionary_release_id": "RELEASE-TEST",
            "automatic_promotion": False,
        }
    ]
    chunks_path = package / "chunks.jsonl"
    relationships_path = package / "chunk_relationships.jsonl"
    _write_jsonl(chunks_path, chunks)
    _write_jsonl(relationships_path, relationships)
    manifest = {
        "schema_version": "0.1",
        "release_id": "CHUNKRELEASE-TEST",
        "dictionary_release_id": "RELEASE-TEST",
        "manifest_status": "CANONICAL_CHUNK_EXPORT",
        "record_counts": {
            "chunks": len(chunks),
            "chunk_relationships": len(relationships),
        },
        "artifacts": {
            path.name: {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "record_count": 1,
            }
            for path in (chunks_path, relationships_path)
        },
        "controls": {
            "source_data_classification": "SYNTHETIC",
            "deidentification_status": "PASS",
            "automatic_promotions": 0,
            "neo4j_writes": 0,
        },
    }
    (package / "chunk_release_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return package


@unittest.skipUnless(
    DICTIONARY_PLAN.is_dir(),
    "preview dictionary plan unavailable",
)
class ChunkReleaseAndPlanTests(unittest.TestCase):
    def test_canonical_chunk_package_is_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            package = _make_chunk_package(Path(temporary))
            report = validate_chunk_package(package)
            self.assertEqual(
                report["status"],
                "PASS_CANONICAL_CHUNK_PACKAGE_ACCEPTED",
            )
            self.assertEqual(report["errors"], [])
            self.assertEqual(report["neo4j_writes"], 0)

    def test_chunk_plan_uses_card_id_and_is_write_free(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = _make_chunk_package(root)
            output = root / "plan"
            report = build_chunk_context_plan(
                package,
                DICTIONARY_PLAN,
                output,
            )
            self.assertEqual(
                report["status"],
                "PASS_WRITE_FREE_CHUNK_GRAPH_PLAN",
            )
            self.assertEqual(
                report["controls"]["all_card_endpoints_exist"],
                True,
            )
            self.assertEqual(
                report["controls"]["pending_context_queue_included"],
                0,
            )
            self.assertEqual(report["controls"]["neo4j_writes"], 0)
            edge = json.loads(
                (
                    output / "chunk_dictionary_edges.jsonl"
                ).read_text(encoding="utf-8")
            )
            self.assertEqual(
                edge["target_node_key"],
                "GlossaryEntry:A004",
            )

    def test_missing_dictionary_card_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = _make_chunk_package(root, card_id="H999")
            with self.assertRaises(ChunkPlanRejected):
                build_chunk_context_plan(
                    package,
                    DICTIONARY_PLAN,
                    root / "plan",
                )

    def test_direct_identifier_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            package = _make_chunk_package(root)
            chunks_path = package / "chunks.jsonl"
            row = json.loads(chunks_path.read_text(encoding="utf-8"))
            row["deidentified_text"] = "טלפון 050-1234567"
            row["text_sha256"] = hashlib.sha256(
                row["deidentified_text"].encode("utf-8")
            ).hexdigest()
            _write_jsonl(chunks_path, [row])
            manifest_path = package / "chunk_release_manifest.json"
            manifest = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
            manifest["artifacts"]["chunks.jsonl"]["sha256"] = (
                sha256_file(chunks_path)
            )
            manifest["artifacts"]["chunks.jsonl"]["bytes"] = (
                chunks_path.stat().st_size
            )
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            report = validate_chunk_package(package)
            self.assertEqual(
                report["status"],
                "BLOCKED_CHUNK_PACKAGE_REJECTED",
            )
            self.assertTrue(
                any(":pii:phone" in error for error in report["errors"])
            )


if __name__ == "__main__":
    unittest.main()
