# -*- coding: utf-8 -*-

from __future__ import annotations

import copy
import csv
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from dictionary_release_acceptance import (
    canonical_card_hash,
    canonical_manifest_self_hash,
    validate_package,
    validate_record_against_schema,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = REPO_ROOT / "data" / "official_glossary" / "schema.json"
PREVIEW_PATH = Path(
    r"C:\Avihusitton\dherech-dictionery\Derech_Dictionary_Project"
    r"\07_UPDATED_DICTIONARY\CLINICAL_AI_PREVIEW"
)


def valid_record() -> dict[str, object]:
    record: dict[str, object] = {
        "card_id": "A001",
        "status": "APPROVED",
        "dictionary_version": "test",
        "card_hash": "0" * 64,
        "created_at": "2026-07-29T00:00:00Z",
        "updated_at": "2026-07-29T00:00:00Z",
        "entry_name": "ערך בדיקה",
        "entry_type": "CONCEPT",
        "aliases_and_spellings": ["כינוי"],
        "source_based_definition": "הגדרה",
        "unified_definition": "ניסוח",
        "parent_terms": [],
        "child_terms": [],
        "parallel_terms": [],
        "distinguish_from": [],
        "causal_or_developmental_relations": [],
        "related_techniques": [],
        "related_exercises": [],
        "therapeutic_contexts": [],
        "short_example": "",
        "common_mistakes": "",
        "exact_source": "מקור",
        "certainty": "HIGH",
        "editorial_note": "",
        "see_also": [],
    }
    record["card_hash"] = canonical_card_hash(record)
    return record


class RecordValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    def test_valid_record_passes(self) -> None:
        self.assertEqual(
            validate_record_against_schema(valid_record(), self.schema),
            [],
        )

    def test_hash_is_stable_across_key_order(self) -> None:
        record = valid_record()
        reversed_record = dict(reversed(list(record.items())))
        self.assertEqual(
            canonical_card_hash(record),
            canonical_card_hash(reversed_record),
        )

    def test_hash_ignores_release_metadata(self) -> None:
        record = valid_record()
        changed = copy.deepcopy(record)
        changed["dictionary_version"] = "another"
        changed["updated_at"] = "2027-01-01T00:00:00Z"
        self.assertEqual(
            canonical_card_hash(record),
            canonical_card_hash(changed),
        )

    def test_extra_field_is_blocked(self) -> None:
        record = valid_record()
        record["unexpected"] = "value"
        errors = validate_record_against_schema(record, self.schema)
        self.assertTrue(any(error.startswith("extra:") for error in errors))

    def test_bad_card_hash_is_blocked(self) -> None:
        record = valid_record()
        record["card_hash"] = "0" * 64
        self.assertIn(
            "card_hash:mismatch",
            validate_record_against_schema(record, self.schema),
        )


@unittest.skipUnless(PREVIEW_PATH.is_dir(), "dictionary preview is unavailable")
class PreviewIntegrationTests(unittest.TestCase):
    def test_current_preview_passes(self) -> None:
        report = validate_package(PREVIEW_PATH, SCHEMA_PATH)
        self.assertEqual(
            report["status"],
            "PASS_PREVIEW_ACCEPTED_FOR_WRITE_FREE_ADAPTER",
        )
        self.assertEqual(report["neo4j_writes"], 0)
        self.assertFalse(report["eligible_for_neo4j_write"])
        self.assertEqual(report["errors"], [])

    def test_manifest_self_hash_recomputes(self) -> None:
        manifest_path = (
            PREVIEW_PATH / "dictionary_release_manifest.preview.json"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        stored = manifest["artifacts"][manifest_path.name]["sha256"]
        self.assertEqual(
            stored,
            canonical_manifest_self_hash(manifest, manifest_path.name),
        )

    def test_changed_artifact_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy_dir = Path(temporary) / "preview"
            shutil.copytree(PREVIEW_PATH, copy_dir)
            active_path = copy_dir / "ACTIVE_IDS.preview.csv"
            with active_path.open("a", encoding="utf-8", newline="") as handle:
                handle.write("\n")
            report = validate_package(copy_dir, SCHEMA_PATH)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(
                any("sha256_mismatch" in error for error in report["errors"])
            )

    def test_missing_active_endpoint_is_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            copy_dir = Path(temporary) / "preview"
            shutil.copytree(PREVIEW_PATH, copy_dir)
            cross_path = copy_dir / "CROSS_REFERENCES.preview.csv"
            with cross_path.open(
                "r", encoding="utf-8-sig", newline=""
            ) as handle:
                reader = csv.DictReader(handle)
                fieldnames = list(reader.fieldnames or [])
                rows = list(reader)
            rows[0]["target_card_id"] = "H999"
            with cross_path.open(
                "w", encoding="utf-8", newline=""
            ) as handle:
                writer = csv.DictWriter(handle, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
            report = validate_package(copy_dir, SCHEMA_PATH)
            self.assertEqual(report["status"], "BLOCKED")
            self.assertTrue(
                any("inactive_endpoint" in error for error in report["errors"])
            )


if __name__ == "__main__":
    unittest.main()
