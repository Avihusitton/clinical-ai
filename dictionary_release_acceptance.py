# -*- coding: utf-8 -*-
"""Write-free acceptance checks for Derech Dictionary release packages.

The validator treats the dictionary workspace as an external protected producer.
It verifies package identity, hashes, schema shape, identifiers, redirects,
cross-references, provenance and fail-closed controls. It never connects to
Neo4j and never promotes dictionary content.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping


ROLE_FILENAMES = {
    "glossary": ("official_glossary.jsonl", "official_glossary.preview.jsonl"),
    "active_ids": ("ACTIVE_IDS.csv", "ACTIVE_IDS.preview.csv"),
    "redirects": ("REDIRECTS.csv", "REDIRECTS.preview.csv"),
    "cross_references": (
        "CROSS_REFERENCES.csv",
        "CROSS_REFERENCES.preview.csv",
    ),
    "source_map": ("SOURCE_MAP.csv", "SOURCE_MAP.preview.csv"),
    "relation_candidates": (
        "RELATION_CANDIDATES.csv",
        "RELATION_CANDIDATES.preview.csv",
    ),
}
CANONICAL_MANIFEST_STATUSES = {
    "CANONICAL_RELEASE",
    "D4_CANONICAL_RELEASE",
}

EXPECTED_HEADERS = {
    "active_ids": [
        "card_id",
        "entry_name",
        "canonical_status",
        "release_status",
        "complete_19_fields",
    ],
    "redirects": [
        "source_id",
        "source_name",
        "target_id",
        "target_name",
        "redirect_type",
        "outside_expected_range",
        "status",
    ],
    "cross_references": [
        "source_card_id",
        "target_card_id",
        "relation_type",
        "directionality",
        "certainty",
        "review_status",
        "source_document_id",
        "evidence_locator",
    ],
    "source_map": [
        "card_id",
        "source_document_id",
        "source_sha256",
        "source_type",
        "source_authority",
        "evidence_locator",
        "evidence_type",
        "certainty",
    ],
    "relation_candidates": [
        "source_card_id",
        "target_card_id",
        "relation_type",
        "directionality",
        "certainty",
        "review_status",
        "source_document_id",
        "evidence_locator",
        "contradiction_note",
    ],
}

REFERENCE_FIELDS = {
    "parent_terms",
    "child_terms",
    "parallel_terms",
    "distinguish_from",
    "causal_or_developmental_relations",
    "related_techniques",
    "related_exercises",
    "therapeutic_contexts",
    "see_also",
}

VOLATILE_CARD_HASH_FIELDS = {
    "dictionary_version",
    "card_hash",
    "created_at",
    "updated_at",
}

CARD_ID_RE = re.compile(r"^[A-H][0-9]{3}$")
SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
SOURCE_ID_RE = re.compile(r"^SRC-[A-F0-9]{16}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_card_hash(record: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in record.items()
        if key not in VOLATILE_CARD_HASH_FIELDS
    }
    for key, value in list(payload.items()):
        if isinstance(value, list):
            payload[key] = sorted(set(value))
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def canonical_manifest_self_hash(
    manifest: Mapping[str, Any],
    manifest_filename: str,
) -> str:
    payload = copy.deepcopy(dict(manifest))
    artifact = payload["artifacts"][manifest_filename]
    artifact["sha256"] = None
    artifact["bytes"] = None
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path.name}:{line_number}:not_object")
            records.append(value)
    return records


def read_csv_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return list(reader.fieldnames or []), list(reader)


def validate_record_against_schema(
    record: Mapping[str, Any],
    schema: Mapping[str, Any],
) -> list[str]:
    errors: list[str] = []
    required = set(schema.get("required", []))
    properties = schema.get("properties", {})
    missing = sorted(required - set(record))
    extra = sorted(set(record) - set(properties))
    if missing:
        errors.append(f"missing:{','.join(missing)}")
    if schema.get("additionalProperties") is False and extra:
        errors.append(f"extra:{','.join(extra)}")

    for field, spec in properties.items():
        if field not in record:
            continue
        value = record[field]
        expected_type = spec.get("type")
        if expected_type == "string" and not isinstance(value, str):
            errors.append(f"{field}:not_string")
        elif expected_type == "array":
            if not isinstance(value, list) or any(
                not isinstance(item, str) for item in value
            ):
                errors.append(f"{field}:not_string_array")
        if "enum" in spec and value not in spec["enum"]:
            errors.append(f"{field}:enum")
        if (
            "pattern" in spec
            and isinstance(value, str)
            and not re.fullmatch(spec["pattern"], value)
        ):
            errors.append(f"{field}:pattern")

    if record.get("card_hash") != canonical_card_hash(record):
        errors.append("card_hash:mismatch")
    return errors


def _normalize_term(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = normalized.replace("\u200e", "").replace("\u200f", "")
    return " ".join(normalized.casefold().split())


def _resolve_role_path(package_dir: Path, role: str) -> Path | None:
    for filename in ROLE_FILENAMES[role]:
        path = package_dir / filename
        if path.is_file():
            return path
    return None


def _record_count(path: Path) -> int:
    suffix = path.suffix.casefold()
    if suffix == ".jsonl":
        return len(read_jsonl(path))
    if suffix == ".csv":
        return len(read_csv_rows(path)[1])
    return 1 if path.stat().st_size else 0


def _duplicates(values: Iterable[str]) -> list[str]:
    counts = Counter(values)
    return sorted(value for value, count in counts.items() if count > 1)


def validate_package(package_dir: Path, schema_path: Path) -> dict[str, Any]:
    package_dir = Path(package_dir).resolve()
    schema_path = Path(schema_path).resolve()
    errors: list[str] = []
    warnings: list[str] = []

    manifest_paths = sorted(package_dir.glob("dictionary_release_manifest*.json"))
    if len(manifest_paths) != 1:
        return {
            "status": "BLOCKED",
            "errors": [f"manifest_count:{len(manifest_paths)}"],
            "warnings": [],
            "package_dir": str(package_dir),
            "automatic_promotions": 0,
            "neo4j_writes": 0,
        }

    manifest_path = manifest_paths[0]
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    manifest_filename = manifest_path.name
    manifest_status = manifest.get("manifest_status")
    is_preview = manifest_status == "PREVIEW_NOT_A_CANONICAL_RELEASE"
    is_canonical = manifest_status in CANONICAL_MANIFEST_STATUSES
    if not is_preview and not is_canonical:
        errors.append("manifest:status_not_preview_or_canonical")
    release_id = str(manifest.get("release_id") or "")
    if is_preview and not release_id.startswith("PREVIEW-"):
        errors.append("manifest:preview_release_id_invalid")
    if is_canonical and not release_id.startswith(
        ("D4-", "RELEASE-")
    ):
        errors.append("manifest:canonical_release_id_invalid")

    if manifest.get("automatic_promotions") != 0:
        errors.append("manifest:automatic_promotions_not_zero")
    if manifest.get("neo4j_writes") != 0:
        errors.append("manifest:neo4j_writes_not_zero")
    if is_preview and manifest.get("not_for_production_ingestion") is not True:
        errors.append("manifest:preview_not_fail_closed")

    intake_feedback = manifest.get("intake_feedback", {})
    if intake_feedback.get("automatic_promotions") != 0:
        errors.append("manifest:intake_automatic_promotions_not_zero")
    if intake_feedback.get("neo4j_writes") != 0:
        errors.append("manifest:intake_neo4j_writes_not_zero")

    legacy_policy = manifest.get("legacy_policy", {})
    if legacy_policy.get("legacy_is_authoritative") is not False:
        errors.append("manifest:legacy_authority_not_rejected")
    if legacy_policy.get("legacy_compatibility_required") is not False:
        errors.append("manifest:legacy_compatibility_not_rejected")
    if legacy_policy.get("legacy_mapping_created") is not False:
        errors.append("manifest:legacy_mapping_present")
    if legacy_policy.get("legacy_ids_included") != 0:
        errors.append("manifest:legacy_ids_included")

    schema_identity = manifest.get("official_glossary_schema", {})
    local_schema_hash = sha256_file(schema_path)
    if schema_identity.get("sha256") != local_schema_hash:
        errors.append("schema:sha256_mismatch")
    schema = json.loads(schema_path.read_text(encoding="utf-8-sig"))

    artifacts = manifest.get("artifacts", {})
    if manifest_filename not in artifacts:
        errors.append("manifest:self_artifact_missing")
    else:
        stored_self_hash = artifacts[manifest_filename].get("sha256")
        if stored_self_hash != canonical_manifest_self_hash(
            manifest, manifest_filename
        ):
            errors.append("manifest:self_hash_mismatch")

    for artifact_name, expected in artifacts.items():
        artifact_path = package_dir / artifact_name
        if not artifact_path.is_file():
            errors.append(f"artifact:{artifact_name}:missing")
            continue
        if artifact_name == manifest_filename:
            continue
        if expected.get("sha256") != sha256_file(artifact_path):
            errors.append(f"artifact:{artifact_name}:sha256_mismatch")
        if expected.get("bytes") != artifact_path.stat().st_size:
            errors.append(f"artifact:{artifact_name}:byte_count_mismatch")
        expected_count = expected.get("record_count")
        if isinstance(expected_count, int) and expected_count != _record_count(
            artifact_path
        ):
            errors.append(f"artifact:{artifact_name}:record_count_mismatch")

    role_paths: dict[str, Path] = {}
    for role in ROLE_FILENAMES:
        path = _resolve_role_path(package_dir, role)
        if path is None:
            errors.append(f"role:{role}:missing")
        else:
            role_paths[role] = path

    if errors and "glossary" not in role_paths:
        return {
            "status": "BLOCKED",
            "manifest_status": manifest_status,
            "release_id": manifest.get("release_id"),
            "errors": sorted(set(errors)),
            "warnings": warnings,
            "package_dir": str(package_dir),
            "automatic_promotions": 0,
            "neo4j_writes": 0,
        }

    records = read_jsonl(role_paths["glossary"])
    records_by_id: dict[str, dict[str, Any]] = {}
    for index, record in enumerate(records, start=1):
        card_id = str(record.get("card_id", f"LINE-{index}"))
        record_errors = validate_record_against_schema(record, schema)
        errors.extend(
            f"glossary:{card_id}:{error}" for error in record_errors
        )
        if not CARD_ID_RE.fullmatch(card_id):
            errors.append(f"glossary:{card_id}:outside_A_to_H")
        if card_id in records_by_id:
            errors.append(f"glossary:{card_id}:duplicate")
        else:
            records_by_id[card_id] = record

    csv_data: dict[str, list[dict[str, str]]] = {}
    for role, expected_header in EXPECTED_HEADERS.items():
        if role not in role_paths:
            csv_data[role] = []
            continue
        header, rows = read_csv_rows(role_paths[role])
        if header != expected_header:
            errors.append(f"csv:{role}:header_mismatch")
        csv_data[role] = rows

    active_rows = csv_data["active_ids"]
    active_ids_list = [row.get("card_id", "") for row in active_rows]
    active_ids = set(active_ids_list)
    for duplicate in _duplicates(active_ids_list):
        errors.append(f"active_ids:{duplicate}:duplicate")
    for card_id in active_ids:
        if not CARD_ID_RE.fullmatch(card_id):
            errors.append(f"active_ids:{card_id}:outside_A_to_H")
        record = records_by_id.get(card_id)
        if record is None:
            errors.append(f"active_ids:{card_id}:record_missing")
        elif record.get("status") in {"DEPRECATED", "ARCHIVED"}:
            errors.append(f"active_ids:{card_id}:inactive_record")

    expected_active_ids = {
        card_id
        for card_id, record in records_by_id.items()
        if record.get("status") not in {"DEPRECATED", "ARCHIVED"}
    }
    if active_ids != expected_active_ids:
        errors.append("active_ids:set_mismatch_with_glossary")
    if is_canonical:
        for card_id in active_ids:
            record = records_by_id.get(card_id, {})
            if record.get("status") != "APPROVED":
                errors.append(
                    f"active_ids:{card_id}:canonical_not_approved"
                )
            if record.get("certainty") == "PROVISIONAL":
                errors.append(
                    f"active_ids:{card_id}:canonical_provisional"
                )

    alias_owners: dict[str, set[str]] = {}
    for card_id in active_ids:
        record = records_by_id.get(card_id, {})
        terms = [record.get("entry_name", "")]
        terms.extend(record.get("aliases_and_spellings", []))
        for term in terms:
            normalized = _normalize_term(str(term))
            if normalized:
                alias_owners.setdefault(normalized, set()).add(card_id)
    for term, owners in sorted(alias_owners.items()):
        if len(owners) > 1:
            errors.append(
                f"aliases:collision:{term}:{','.join(sorted(owners))}"
            )

    redirect_rows = csv_data["redirects"]
    redirect_sources = [row.get("source_id", "") for row in redirect_rows]
    redirect_source_set = set(redirect_sources)
    for duplicate in _duplicates(redirect_sources):
        errors.append(f"redirects:{duplicate}:duplicate_source")
    for row in redirect_rows:
        source_id = row.get("source_id", "")
        target_id = row.get("target_id", "")
        if source_id in active_ids:
            errors.append(f"redirects:{source_id}:source_is_active")
        if target_id not in active_ids:
            errors.append(f"redirects:{source_id}:target_not_active")
        if target_id in redirect_source_set:
            errors.append(f"redirects:{source_id}:redirect_chain")
        source_record = records_by_id.get(source_id)
        if source_record is None:
            errors.append(f"redirects:{source_id}:record_missing")
        elif source_record.get("status") != "DEPRECATED":
            errors.append(f"redirects:{source_id}:record_not_deprecated")
        elif target_id not in source_record.get("see_also", []):
            errors.append(f"redirects:{source_id}:target_not_in_see_also")

    for card_id, record in records_by_id.items():
        for field in REFERENCE_FIELDS:
            for target_id in record.get(field, []):
                if not CARD_ID_RE.fullmatch(target_id):
                    errors.append(
                        f"glossary:{card_id}:{field}:non_identifier_reference"
                    )
                elif target_id not in active_ids:
                    errors.append(
                        f"glossary:{card_id}:{field}:{target_id}:target_not_active"
                    )

    approved_edge_keys: set[tuple[str, str, str]] = set()
    for row in csv_data["cross_references"]:
        source_id = row.get("source_card_id", "")
        target_id = row.get("target_card_id", "")
        relation_type = row.get("relation_type", "")
        if source_id not in active_ids or target_id not in active_ids:
            errors.append(
                f"cross_reference:{source_id}:{relation_type}:{target_id}:inactive_endpoint"
            )
        if row.get("review_status") != "APPROVED_DICTIONARY":
            errors.append(
                f"cross_reference:{source_id}:{relation_type}:{target_id}:not_approved"
            )
        key = (source_id, relation_type, target_id)
        if key in approved_edge_keys:
            errors.append(
                f"cross_reference:{source_id}:{relation_type}:{target_id}:duplicate"
            )
        approved_edge_keys.add(key)
        if not SOURCE_ID_RE.fullmatch(row.get("source_document_id", "")):
            errors.append(
                f"cross_reference:{source_id}:{relation_type}:{target_id}:invalid_source_id"
            )

    for row in csv_data["relation_candidates"]:
        source_id = row.get("source_card_id", "")
        target_id = row.get("target_card_id", "")
        relation_type = row.get("relation_type", "")
        if source_id not in active_ids or target_id not in active_ids:
            errors.append(
                f"relation_candidate:{source_id}:{relation_type}:{target_id}:inactive_endpoint"
            )
        if row.get("review_status") != "PENDING_DICTIONARY_REVIEW":
            errors.append(
                f"relation_candidate:{source_id}:{relation_type}:{target_id}:invalid_review_status"
            )
        if (source_id, relation_type, target_id) in approved_edge_keys:
            errors.append(
                f"relation_candidate:{source_id}:{relation_type}:{target_id}:already_approved"
            )
        if not SOURCE_ID_RE.fullmatch(row.get("source_document_id", "")):
            errors.append(
                f"relation_candidate:{source_id}:{relation_type}:{target_id}:invalid_source_id"
            )

    source_map_card_ids: set[str] = set()
    source_ids: set[str] = set()
    source_identity_by_id: dict[str, tuple[str, str, str]] = {}
    for row in csv_data["source_map"]:
        card_id = row.get("card_id", "")
        source_id = row.get("source_document_id", "")
        source_sha = row.get("source_sha256", "")
        source_map_card_ids.add(card_id)
        source_ids.add(source_id)
        if card_id not in records_by_id:
            errors.append(f"source_map:{card_id}:record_missing")
        if not SHA256_RE.fullmatch(source_sha):
            errors.append(f"source_map:{card_id}:invalid_sha256")
        if (
            not SOURCE_ID_RE.fullmatch(source_id)
            or source_id != f"SRC-{source_sha[:16].upper()}"
        ):
            errors.append(f"source_map:{card_id}:source_id_hash_mismatch")
        source_identity = (
            source_sha,
            row.get("source_type", ""),
            row.get("source_authority", ""),
        )
        prior_identity = source_identity_by_id.setdefault(
            source_id, source_identity
        )
        if prior_identity != source_identity:
            errors.append(
                f"source_map:{source_id}:inconsistent_source_identity"
            )
    if set(records_by_id) - source_map_card_ids:
        errors.append("source_map:missing_glossary_records")

    for role in ("cross_references", "relation_candidates"):
        for row in csv_data[role]:
            if row.get("source_document_id", "") not in source_ids:
                errors.append(
                    f"{role}:source_document_id_not_in_source_map"
                )

    counts = {
        "glossary_records": len(records),
        "active_ids": len(active_ids),
        "redirects": len(redirect_rows),
        "cross_references": len(csv_data["cross_references"]),
        "source_map_rows": len(csv_data["source_map"]),
        "relation_candidates": len(csv_data["relation_candidates"]),
    }
    manifest_counts = manifest.get("record_counts", {})
    if is_canonical and manifest_counts.get("blocked_cards") != 0:
        errors.append("manifest:canonical_blocked_cards_not_zero")
    count_mapping = {
        "total_documented_ids": "glossary_records",
        "redirects": "redirects",
        "cross_references": "cross_references",
        "source_map_rows": "source_map_rows",
        "relation_candidates": "relation_candidates",
    }
    for manifest_key, report_key in count_mapping.items():
        if manifest_counts.get(manifest_key) != counts[report_key]:
            errors.append(f"manifest:record_counts:{manifest_key}:mismatch")

    status_counts = Counter(
        str(record.get("status", "")) for record in records
    )
    for status_name in ("APPROVED", "DRAFT", "ARCHIVED", "DEPRECATED"):
        if manifest_counts.get(status_name) != status_counts[status_name]:
            errors.append(
                f"manifest:record_counts:{status_name}:mismatch"
            )

    unique_errors = sorted(set(errors))
    if unique_errors:
        status = "BLOCKED"
    elif is_preview:
        status = "PASS_PREVIEW_ACCEPTED_FOR_WRITE_FREE_ADAPTER"
    else:
        status = "PASS_CANONICAL_PACKAGE_ACCEPTED_FOR_PREFLIGHT"

    return {
        "schema_version": "0.1",
        "status": status,
        "manifest_status": manifest_status,
        "release_id": manifest.get("release_id"),
        "dictionary_version": manifest.get("dictionary_version"),
        "package_dir": str(package_dir),
        "manifest_path": str(manifest_path),
        "manifest_actual_sha256": sha256_file(manifest_path),
        "manifest_canonical_self_sha256": artifacts.get(
            manifest_filename, {}
        ).get("sha256"),
        "schema_sha256": local_schema_hash,
        "counts": counts,
        "errors": unique_errors,
        "warnings": warnings,
        "canonical_source_resolved": is_canonical and not unique_errors,
        "eligible_for_write_free_adapter": not unique_errors,
        "eligible_for_neo4j_write": False,
        "automatic_promotions": 0,
        "neo4j_writes": 0,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("data/official_glossary/schema.json"),
    )
    parser.add_argument("--report", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = validate_package(args.package_dir, args.schema)
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
