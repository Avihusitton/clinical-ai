import json
import shutil
import unittest
import uuid
from pathlib import Path

from material_intake_router import (
    IntakeContractError,
    ROUTE_CANONICAL,
    ROUTE_QUARANTINE,
    ROUTE_SUPPLEMENTAL,
    append_source_record,
    build_source_record,
    route_candidate,
    route_file,
)


SHA = "a" * 64
EVIDENCE = [
    {
        "chunk_id": "chunk-1",
        "source_location": "page 2",
        "evidence_hash": "b" * 64,
    }
]


def candidate(**overrides):
    value = {
        "candidate_id": "CAND-001",
        "source_document_id": "SRC-AAAAAAAAAAAAAAAA",
        "source_sha256": SHA,
        "source_authority": "METHOD_PRIMARY",
        "source_authority_basis": "OWNER_DECLARATION",
        "candidate_kind": "NEW_CANONICAL_ENTRY",
        "candidate_label": "מושג בדיקה",
        "anchor_card_ids": [],
        "evidence_refs": EVIDENCE,
        "pii_status": "CLEAR",
        "rights_status": "CLEARED",
    }
    value.update(overrides)
    return value


class MaterialIntakeRouterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = (
            Path.cwd() / "out" / f"material_intake_test_{uuid.uuid4().hex}"
        )
        self.temp_dir.mkdir(parents=True)

    def tearDown(self):
        resolved = self.temp_dir.resolve()
        expected_parent = (Path.cwd() / "out").resolve()
        if expected_parent not in resolved.parents:
            raise AssertionError(f"Unsafe test cleanup target: {resolved}")
        shutil.rmtree(resolved, ignore_errors=True)

    def test_primary_new_entry_routes_to_canonical_review(self):
        routed = route_candidate(candidate())
        self.assertEqual(routed["route"], ROUTE_CANONICAL)
        self.assertEqual(routed["review_status"], "PENDING_DICTIONARY_REVIEW")
        self.assertEqual(routed["blocking_reasons"], [])

    def test_primary_relation_routes_to_supplemental_review(self):
        routed = route_candidate(
            candidate(
                candidate_kind="RELATION",
                anchor_card_ids=["A001", "A002"],
                relation_type="RELATED_TO",
            )
        )
        self.assertEqual(routed["route"], ROUTE_SUPPLEMENTAL)

    def test_secondary_subconcept_routes_to_supplemental_review(self):
        routed = route_candidate(
            candidate(
                source_authority="SECONDARY_INTERPRETIVE",
                source_authority_basis="PATH_DECLARATION",
                candidate_kind="SUBCONCEPT",
                anchor_card_ids=["H001"],
            )
        )
        self.assertEqual(routed["route"], ROUTE_SUPPLEMENTAL)

    def test_secondary_cannot_define_canonical_entry(self):
        routed = route_candidate(
            candidate(
                source_authority="SECONDARY_INTERPRETIVE",
                source_authority_basis="PATH_DECLARATION",
            )
        )
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn(
            "SECONDARY_CANNOT_DEFINE_CANONICAL_ENTRY",
            routed["blocking_reasons"],
        )

    def test_secondary_candidate_requires_canonical_anchor(self):
        routed = route_candidate(
            candidate(
                source_authority="SECONDARY_INTERPRETIVE",
                source_authority_basis="PATH_DECLARATION",
                candidate_kind="SUBCONCEPT",
            )
        )
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn(
            "SUPPLEMENTAL_CANDIDATE_REQUIRES_ANCHOR",
            routed["blocking_reasons"],
        )

    def test_unverified_source_fails_closed(self):
        routed = route_candidate(
            candidate(
                source_authority="UNVERIFIED",
                source_authority_basis="UNVERIFIED",
            )
        )
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn("SOURCE_AUTHORITY_UNVERIFIED", routed["blocking_reasons"])

    def test_pii_blocks_before_handoff(self):
        routed = route_candidate(candidate(pii_status="BLOCKED"))
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn("PII_NOT_CLEAR", routed["blocking_reasons"])

    def test_rights_block_before_handoff(self):
        routed = route_candidate(candidate(rights_status="UNVERIFIED"))
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn("RIGHTS_NOT_CLEARED", routed["blocking_reasons"])

    def test_relation_requires_two_anchors_and_type(self):
        routed = route_candidate(
            candidate(candidate_kind="RELATION", anchor_card_ids=["A001"])
        )
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn("RELATION_REQUIRES_TWO_ANCHORS", routed["blocking_reasons"])
        self.assertIn("RELATION_TYPE_REQUIRED", routed["blocking_reasons"])

    def test_unexpected_fields_are_quarantined(self):
        routed = route_candidate(candidate(approved=True))
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn("UNEXPECTED_FIELDS:approved", routed["blocking_reasons"])

    def test_source_document_id_requires_exact_contract_pattern(self):
        routed = route_candidate(candidate(source_document_id="SRC-not-strict"))
        self.assertEqual(routed["route"], ROUTE_QUARANTINE)
        self.assertIn("INVALID_SOURCE_DOCUMENT_ID", routed["blocking_reasons"])

    def test_route_file_writes_separate_queues_and_zero_promotions(self):
        source = self.temp_dir / "candidates.jsonl"
        rows = [
            candidate(candidate_id="CAND-PRIMARY"),
            candidate(
                candidate_id="CAND-SECONDARY",
                source_document_id="SRC-CCCCCCCCCCCCCCCC",
                source_sha256="c" * 64,
                source_authority="SECONDARY_INTERPRETIVE",
                source_authority_basis="PATH_DECLARATION",
                candidate_kind="EXAMPLE",
                anchor_card_ids=["A001"],
            ),
            candidate(
                candidate_id="CAND-BLOCKED",
                source_authority="UNVERIFIED",
                source_authority_basis="UNVERIFIED",
            ),
        ]
        source.write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
            encoding="utf-8",
        )
        registry = self.temp_dir / "source_registry.jsonl"
        registry_rows = [
            {
                "source_document_id": "SRC-AAAAAAAAAAAAAAAA",
                "sha256": SHA,
                "file_name": "synthetic.docx",
                "source_authority": "METHOD_PRIMARY",
                "source_type": "METHOD_BOOK",
                "source_authority_basis": "OWNER_DECLARATION",
                "declared_by": "project-owner",
                "registered_at": "2026-07-28T00:00:00Z",
                "pii_status": "CLEAR",
                "rights_status": "CLEARED",
                "pipeline_status": "CLINICAL_PIPELINE_COMPLETE",
            },
            {
                "source_document_id": "SRC-CCCCCCCCCCCCCCCC",
                "sha256": "c" * 64,
                "file_name": "student-summary.docx",
                "source_authority": "SECONDARY_INTERPRETIVE",
                "source_type": "STUDENT_SUMMARY",
                "source_authority_basis": "PATH_DECLARATION",
                "declared_by": "approved-collection-rule",
                "registered_at": "2026-07-28T00:00:00Z",
                "pii_status": "CLEAR",
                "rights_status": "CLEARED",
                "pipeline_status": "CLINICAL_PIPELINE_COMPLETE",
            },
        ]
        registry.write_text(
            "".join(
                json.dumps(row, ensure_ascii=False) + "\n"
                for row in registry_rows
            ),
            encoding="utf-8",
        )

        report = route_file(
            source,
            self.temp_dir / "routed",
            registry,
            generated_at="2026-07-28T00:00:00Z",
        )

        self.assertEqual(report["route_counts"][ROUTE_CANONICAL], 1)
        self.assertEqual(report["route_counts"][ROUTE_SUPPLEMENTAL], 1)
        self.assertEqual(report["route_counts"][ROUTE_QUARANTINE], 1)
        self.assertEqual(report["automatic_promotions"], 0)
        self.assertEqual(report["neo4j_writes"], 0)
        self.assertEqual(
            report["package_status"],
            "READY_FOR_DICTIONARY_VALIDATION",
        )

        quarantine_rows = [
            json.loads(line)
            for line in (
                self.temp_dir / "routed" / "quarantine.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        ]
        self.assertNotIn("candidate_label", quarantine_rows[0])
        self.assertNotIn("candidate_text", quarantine_rows[0])
        manifest = json.loads(
            (
                self.temp_dir / "routed" / "intake_package_manifest.json"
            ).read_text(encoding="utf-8")
        )
        self.assertTrue(manifest["package_id"].startswith("PKG-"))
        self.assertEqual(manifest["automatic_promotions"], 0)

    def test_source_registration_is_hash_based_and_idempotent(self):
        source = self.temp_dir / "method.docx"
        source.write_bytes(b"synthetic method source")
        registry = self.temp_dir / "source_registry.jsonl"
        record = build_source_record(
            source,
            source_authority="METHOD_PRIMARY",
            source_type="METHOD_BOOK",
            authority_basis="OWNER_DECLARATION",
            declared_by="project-owner",
            registered_at="2026-07-28T00:00:00Z",
        )

        self.assertTrue(append_source_record(registry, record))
        self.assertFalse(append_source_record(registry, record))
        self.assertTrue(record["source_document_id"].startswith("SRC-"))
        self.assertEqual(
            len(registry.read_text(encoding="utf-8").splitlines()),
            1,
        )

    def test_route_file_quarantines_duplicate_candidate_ids(self):
        source = self.temp_dir / "duplicates.jsonl"
        source.write_text(
            "".join(
                json.dumps(candidate(), ensure_ascii=False) + "\n"
                for _ in range(2)
            ),
            encoding="utf-8",
        )
        registry = self.temp_dir / "source_registry.jsonl"
        registry.write_text(
            json.dumps(
                {
                    "source_document_id": "SRC-AAAAAAAAAAAAAAAA",
                    "sha256": SHA,
                    "file_name": "synthetic.docx",
                    "source_authority": "METHOD_PRIMARY",
                    "source_type": "METHOD_BOOK",
                    "source_authority_basis": "OWNER_DECLARATION",
                    "declared_by": "project-owner",
                    "registered_at": "2026-07-28T00:00:00Z",
                    "pii_status": "CLEAR",
                    "rights_status": "CLEARED",
                    "pipeline_status": "CLINICAL_PIPELINE_COMPLETE",
                },
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )

        report = route_file(source, self.temp_dir / "duplicate-routed", registry)

        self.assertEqual(report["route_counts"][ROUTE_CANONICAL], 0)
        self.assertEqual(report["route_counts"][ROUTE_QUARANTINE], 2)
        receipts = [
            json.loads(line)
            for line in (
                self.temp_dir / "duplicate-routed" / "quarantine.jsonl"
            ).read_text(encoding="utf-8").splitlines()
        ]
        self.assertTrue(
            all(
                "DUPLICATE_CANDIDATE_ID" in row["blocking_reasons"]
                for row in receipts
            )
        )

    def test_primary_registration_rejects_unverified_basis(self):
        source = self.temp_dir / "method.docx"
        source.write_bytes(b"synthetic method source")
        with self.assertRaises(IntakeContractError):
            build_source_record(
                source,
                source_authority="METHOD_PRIMARY",
                source_type="METHOD_BOOK",
                authority_basis="PATH_DECLARATION",
                declared_by="project-owner",
            )


if __name__ == "__main__":
    unittest.main()
