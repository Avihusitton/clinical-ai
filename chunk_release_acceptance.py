# -*- coding: utf-8 -*-
"""Validate a durable, de-identified chunk export without DB access."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from dictionary_release_acceptance import sha256_file


CHUNK_ID_PATTERN = re.compile(r"^[a-f0-9]{24}$")
CARD_ID_PATTERN = re.compile(r"^[A-H][0-9]{3}$")
SOURCE_ID_PATTERN = re.compile(r"^SRC-[A-F0-9]{16}$")
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
EMAIL_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+972[- ]?|0)(?:[23489]|5\d)[- ]?\d{3}[- ]?\d{4}(?!\d)"
)
ISRAELI_ID_PATTERN = re.compile(r"(?<!\d)\d{9}(?!\d)")
ALLOWED_RELATIONS = {"HAS_CANDIDATE", "LINKED_TO"}
ALLOWED_TEMPORAL_STATUS = {
    "anchored",
    "timeless",
    "low_confidence",
}
ALLOWED_MODALITY = {
    "individual",
    "couples",
    "family",
    "general",
}
ALLOWED_DATA_CLASSIFICATION = {"NO_PATIENT_DATA", "SYNTHETIC"}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8-sig").splitlines(),
        start=1,
    ):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(
                f"{path.name}:{line_number}:invalid_json"
            ) from error
        if not isinstance(row, dict):
            raise ValueError(
                f"{path.name}:{line_number}:record_not_object"
            )
        rows.append(row)
    return rows


def _manifest_artifact_errors(
    package_dir: Path,
    manifest: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    for name in ("chunks.jsonl", "chunk_relationships.jsonl"):
        expected = manifest.get("artifacts", {}).get(name)
        path = package_dir / name
        if not isinstance(expected, dict):
            errors.append(f"manifest:{name}:missing")
            continue
        if not path.is_file():
            errors.append(f"artifact:{name}:missing")
            continue
        if sha256_file(path) != expected.get("sha256"):
            errors.append(f"artifact:{name}:sha256_mismatch")
        if path.stat().st_size != expected.get("bytes"):
            errors.append(f"artifact:{name}:byte_count_mismatch")
        if len(_read_jsonl(path)) != expected.get("record_count"):
            errors.append(f"artifact:{name}:record_count_mismatch")
    return errors


def _pii_findings(text: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in (
        ("email", EMAIL_PATTERN),
        ("phone", PHONE_PATTERN),
        ("israeli_id_candidate", ISRAELI_ID_PATTERN),
    ):
        if pattern.search(text):
            findings.append(label)
    return findings


def validate_chunk_package(package_dir: Path) -> dict[str, Any]:
    """Validate durable chunks and approved chunk-to-dictionary edges."""
    package_dir = Path(package_dir).resolve()
    manifest_path = package_dir / "chunk_release_manifest.json"
    if not manifest_path.is_file():
        return {
            "status": "BLOCKED_CHUNK_PACKAGE_REJECTED",
            "errors": ["manifest:missing"],
            "warnings": [],
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        }
    manifest = json.loads(
        manifest_path.read_text(encoding="utf-8-sig")
    )
    errors = _manifest_artifact_errors(package_dir, manifest)
    warnings: list[str] = []
    controls = manifest.get("controls", {})
    if manifest.get("manifest_status") != "CANONICAL_CHUNK_EXPORT":
        errors.append("manifest:not_canonical_chunk_export")
    if not str(manifest.get("dictionary_release_id", "")).startswith(
        ("RELEASE-", "D4-")
    ):
        errors.append("manifest:canonical_dictionary_release_required")
    if controls.get("automatic_promotions") != 0:
        errors.append("manifest:automatic_promotions_not_zero")
    if controls.get("neo4j_writes") != 0:
        errors.append("manifest:neo4j_writes_not_zero")
    if controls.get("deidentification_status") != "PASS":
        errors.append("manifest:deidentification_not_pass")
    if controls.get("source_data_classification") not in (
        ALLOWED_DATA_CLASSIFICATION
    ):
        errors.append("manifest:patient_data_not_forbidden")

    chunks_path = package_dir / "chunks.jsonl"
    relationships_path = package_dir / "chunk_relationships.jsonl"
    chunks = _read_jsonl(chunks_path) if chunks_path.is_file() else []
    relationships = (
        _read_jsonl(relationships_path)
        if relationships_path.is_file()
        else []
    )
    known_chunks: set[str] = set()
    for row_number, row in enumerate(chunks, start=1):
        prefix = f"chunks:{row_number}"
        chunk_id = str(row.get("chunk_id", ""))
        if not CHUNK_ID_PATTERN.fullmatch(chunk_id):
            errors.append(f"{prefix}:invalid_chunk_id")
        elif chunk_id in known_chunks:
            errors.append(f"{prefix}:duplicate_chunk_id")
        known_chunks.add(chunk_id)
        if not str(row.get("doc_id", "")).strip():
            errors.append(f"{prefix}:missing_doc_id")
        if not SOURCE_ID_PATTERN.fullmatch(
            str(row.get("source_document_id", ""))
        ):
            errors.append(f"{prefix}:invalid_source_document_id")
        for field in ("source_file_sha256", "text_sha256"):
            if not SHA256_PATTERN.fullmatch(str(row.get(field, ""))):
                errors.append(f"{prefix}:invalid_{field}")
        text = row.get("deidentified_text")
        if not isinstance(text, str) or not text.strip():
            errors.append(f"{prefix}:missing_deidentified_text")
        else:
            expected_text_hash = hashlib.sha256(
                text.encode("utf-8")
            ).hexdigest()
            if expected_text_hash != row.get("text_sha256"):
                errors.append(f"{prefix}:text_sha256_mismatch")
            for finding in _pii_findings(text):
                errors.append(f"{prefix}:pii:{finding}")
        paragraph_range = row.get("paragraph_range")
        if (
            not isinstance(paragraph_range, list)
            or len(paragraph_range) != 2
            or not all(isinstance(item, int) for item in paragraph_range)
            or paragraph_range[0] > paragraph_range[1]
        ):
            errors.append(f"{prefix}:invalid_paragraph_range")
        if row.get("temporal_status") not in ALLOWED_TEMPORAL_STATUS:
            errors.append(f"{prefix}:invalid_temporal_status")
        if row.get("modality") not in ALLOWED_MODALITY:
            errors.append(f"{prefix}:invalid_modality")
        if not isinstance(row.get("heading_path"), list):
            errors.append(f"{prefix}:invalid_heading_path")
        if row.get("deidentification_status") != "PASS":
            errors.append(f"{prefix}:deidentification_not_pass")
        if row.get("data_classification") not in (
            ALLOWED_DATA_CLASSIFICATION
        ):
            errors.append(f"{prefix}:patient_data_not_forbidden")

    known_edges: set[str] = set()
    for row_number, row in enumerate(relationships, start=1):
        prefix = f"relationships:{row_number}"
        edge_id = str(row.get("edge_id", ""))
        if not edge_id.startswith("CHUNKEDGE-"):
            errors.append(f"{prefix}:invalid_edge_id")
        elif edge_id in known_edges:
            errors.append(f"{prefix}:duplicate_edge_id")
        known_edges.add(edge_id)
        if row.get("chunk_id") not in known_chunks:
            errors.append(f"{prefix}:missing_chunk_endpoint")
        if not CARD_ID_PATTERN.fullmatch(
            str(row.get("card_id", ""))
        ):
            errors.append(f"{prefix}:invalid_card_id")
        relation_type = row.get("relation_type")
        if relation_type not in ALLOWED_RELATIONS:
            errors.append(f"{prefix}:invalid_relation_type")
        if row.get("dictionary_release_id") != manifest.get(
            "dictionary_release_id"
        ):
            errors.append(f"{prefix}:dictionary_release_mismatch")
        if row.get("automatic_promotion") is not False:
            errors.append(f"{prefix}:automatic_promotion_not_false")
        if relation_type == "LINKED_TO":
            if row.get("review_status") != "VERIFIED":
                errors.append(f"{prefix}:linked_to_not_verified")
            if not str(row.get("verification_id", "")).strip():
                errors.append(f"{prefix}:missing_verification_id")
        elif row.get("review_status") != "DETERMINISTIC_CANDIDATE":
            errors.append(f"{prefix}:candidate_status_invalid")

    unique_errors = sorted(set(errors))
    manifest_counts = manifest.get("record_counts", {})
    if manifest_counts.get("chunks") != len(chunks):
        unique_errors.append("manifest:chunk_count_mismatch")
    if manifest_counts.get("chunk_relationships") != len(
        relationships
    ):
        unique_errors.append("manifest:relationship_count_mismatch")

    return {
        "status": (
            "PASS_CANONICAL_CHUNK_PACKAGE_ACCEPTED"
            if not unique_errors
            else "BLOCKED_CHUNK_PACKAGE_REJECTED"
        ),
        "manifest_path": str(manifest_path),
        "manifest_sha256": sha256_file(manifest_path),
        "dictionary_release_id": manifest.get(
            "dictionary_release_id"
        ),
        "counts": {
            "chunks": len(chunks),
            "chunk_relationships": len(relationships),
            "has_candidate": sum(
                row.get("relation_type") == "HAS_CANDIDATE"
                for row in relationships
            ),
            "linked_to": sum(
                row.get("relation_type") == "LINKED_TO"
                for row in relationships
            ),
        },
        "errors": sorted(set(unique_errors)),
        "warnings": warnings,
        "automatic_promotions": 0,
        "neo4j_connections": 0,
        "neo4j_writes": 0,
        "eligible_for_write_free_graph_plan": not unique_errors,
        "eligible_for_production_execution": False,
    }
