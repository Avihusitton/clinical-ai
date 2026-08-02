# -*- coding: utf-8 -*-
"""Fail-closed routing for new material flowing from Clinical AI to the dictionary.

This module is deliberately isolated from the protected ingestion and Neo4j
paths.  It registers source identity and routes already-sanitized concept
candidates into review queues.  It never promotes a candidate automatically.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


SOURCE_AUTHORITIES = {
    "METHOD_PRIMARY",
    "SECONDARY_INTERPRETIVE",
    "UNVERIFIED",
}
SOURCE_AUTHORITY_BASES = {
    "OWNER_DECLARATION",
    "SIGNED_PRODUCER_MANIFEST",
    "APPROVED_COLLECTION_RULE",
    "PATH_DECLARATION",
    "UNVERIFIED",
}
PRIMARY_AUTHORITY_BASES = {
    "OWNER_DECLARATION",
    "SIGNED_PRODUCER_MANIFEST",
    "APPROVED_COLLECTION_RULE",
}
CANDIDATE_KINDS = {
    "NEW_CANONICAL_ENTRY",
    "CANONICAL_UPDATE",
    "SUBCONCEPT",
    "RELATION",
    "EXAMPLE",
}
SUPPLEMENTAL_KINDS = {"SUBCONCEPT", "RELATION", "EXAMPLE"}
SOURCE_TYPES = {
    "METHOD_BOOK",
    "METHOD_HANDOUT",
    "METHOD_TRANSCRIPT",
    "STUDENT_SUMMARY",
    "PRACTITIONER_NOTE",
    "OTHER",
}
SOURCE_HANDOFF_PIPELINE_STATUSES = {
    "CLINICAL_PIPELINE_COMPLETE",
    "CANDIDATES_EXPORTED",
}
ROUTE_CANONICAL = "DICTIONARY_CANONICAL_REVIEW"
ROUTE_SUPPLEMENTAL = "DICTIONARY_SUPPLEMENTAL_REVIEW"
ROUTE_QUARANTINE = "QUARANTINE"

_CARD_ID_RE = re.compile(r"^[A-H][0-9]{3}$")
_SHA256_RE = re.compile(r"^[a-f0-9]{64}$")
_SOURCE_DOCUMENT_ID_RE = re.compile(r"^SRC-[A-F0-9]{16}$")
_INPUT_REQUIRED_FIELDS = {
    "candidate_id",
    "source_document_id",
    "source_sha256",
    "source_authority",
    "source_authority_basis",
    "candidate_kind",
    "candidate_label",
    "anchor_card_ids",
    "evidence_refs",
    "pii_status",
    "rights_status",
}
_INPUT_OPTIONAL_FIELDS = {
    "candidate_text",
    "relation_type",
    "confidence",
    "notes",
}
_INPUT_ALLOWED_FIELDS = _INPUT_REQUIRED_FIELDS | _INPUT_OPTIONAL_FIELDS


class IntakeContractError(ValueError):
    """Raised when registration cannot be performed safely."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def build_source_record(
    path: Path,
    *,
    source_authority: str,
    source_type: str,
    authority_basis: str,
    declared_by: str,
    registered_at: str | None = None,
) -> dict[str, Any]:
    """Create a source registry record without copying or processing the file."""
    path = Path(path)
    if not path.is_file():
        raise IntakeContractError(f"Source file does not exist: {path}")
    if source_authority not in SOURCE_AUTHORITIES:
        raise IntakeContractError(f"Unsupported source authority: {source_authority}")
    if source_type not in SOURCE_TYPES:
        raise IntakeContractError(f"Unsupported source type: {source_type}")
    if authority_basis not in SOURCE_AUTHORITY_BASES:
        raise IntakeContractError(f"Unsupported authority basis: {authority_basis}")
    if source_authority == "METHOD_PRIMARY" and authority_basis not in PRIMARY_AUTHORITY_BASES:
        raise IntakeContractError(
            "METHOD_PRIMARY requires an owner declaration, signed producer manifest, "
            "or approved collection rule"
        )
    if not declared_by.strip():
        raise IntakeContractError("declared_by must not be empty")

    digest = sha256_file(path)
    return {
        "source_document_id": f"SRC-{digest[:16].upper()}",
        "sha256": digest,
        "file_name": path.name,
        "source_authority": source_authority,
        "source_type": source_type,
        "source_authority_basis": authority_basis,
        "declared_by": declared_by.strip(),
        "registered_at": registered_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "pii_status": "NOT_SCANNED",
        "rights_status": "UNVERIFIED",
        "pipeline_status": "REGISTERED",
    }


def append_source_record(registry_path: Path, record: Mapping[str, Any]) -> bool:
    """Append idempotently; reject authority conflicts for the same content hash."""
    registry_path = Path(registry_path)
    existing = list(read_jsonl(registry_path)) if registry_path.exists() else []
    same_hash = [item for item in existing if item.get("sha256") == record.get("sha256")]
    for item in same_hash:
        if (
            item.get("source_authority") != record.get("source_authority")
            or item.get("source_authority_basis") != record.get("source_authority_basis")
        ):
            raise IntakeContractError(
                "The same source hash is already registered with conflicting authority"
            )
        return False

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    with registry_path.open("a", encoding="utf-8", newline="\n") as target:
        target.write(json.dumps(dict(record), ensure_ascii=False, sort_keys=True) + "\n")
    return True


def route_candidate(
    candidate: Mapping[str, Any],
    *,
    source_record: Mapping[str, Any] | None = None,
    require_source_registry: bool = False,
    registry_errors: Iterable[str] = (),
) -> dict[str, Any]:
    """Route one candidate and attach a non-promotable review state."""
    record = dict(candidate)
    blockers = _validate_candidate(record)
    blockers.extend(registry_errors)
    blockers.extend(
        _validate_source_link(
            record,
            source_record=source_record,
            require_source_registry=require_source_registry,
        )
    )
    authority = record.get("source_authority")
    kind = record.get("candidate_kind")

    if not blockers:
        if authority == "METHOD_PRIMARY":
            if kind in {"NEW_CANONICAL_ENTRY", "CANONICAL_UPDATE"}:
                route = ROUTE_CANONICAL
            else:
                route = ROUTE_SUPPLEMENTAL
        elif authority == "SECONDARY_INTERPRETIVE":
            if kind not in SUPPLEMENTAL_KINDS:
                blockers.append("SECONDARY_CANNOT_DEFINE_CANONICAL_ENTRY")
                route = ROUTE_QUARANTINE
            else:
                route = ROUTE_SUPPLEMENTAL
        else:
            blockers.append("SOURCE_AUTHORITY_UNVERIFIED")
            route = ROUTE_QUARANTINE
    else:
        route = ROUTE_QUARANTINE

    if not blockers:
        if kind == "CANONICAL_UPDATE" and len(record["anchor_card_ids"]) != 1:
            blockers.append("CANONICAL_UPDATE_REQUIRES_ONE_ANCHOR")
        elif kind in {"SUBCONCEPT", "EXAMPLE"} and not record["anchor_card_ids"]:
            blockers.append("SUPPLEMENTAL_CANDIDATE_REQUIRES_ANCHOR")
        elif kind == "RELATION":
            if len(record["anchor_card_ids"]) < 2:
                blockers.append("RELATION_REQUIRES_TWO_ANCHORS")
            if not str(record.get("relation_type", "")).strip():
                blockers.append("RELATION_TYPE_REQUIRED")

    if blockers:
        route = ROUTE_QUARANTINE

    record["route"] = route
    record["review_status"] = (
        "BLOCKED" if route == ROUTE_QUARANTINE else "PENDING_DICTIONARY_REVIEW"
    )
    record["blocking_reasons"] = sorted(set(blockers))
    return record


def _validate_candidate(record: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    missing = sorted(_INPUT_REQUIRED_FIELDS - record.keys())
    if missing:
        blockers.append("MISSING_REQUIRED_FIELDS:" + ",".join(missing))

    unexpected = sorted(set(record) - _INPUT_ALLOWED_FIELDS)
    if unexpected:
        blockers.append("UNEXPECTED_FIELDS:" + ",".join(unexpected))

    if record.get("source_authority") not in SOURCE_AUTHORITIES:
        blockers.append("INVALID_SOURCE_AUTHORITY")
    if record.get("source_authority_basis") not in SOURCE_AUTHORITY_BASES:
        blockers.append("INVALID_SOURCE_AUTHORITY_BASIS")
    if (
        record.get("source_authority") == "METHOD_PRIMARY"
        and record.get("source_authority_basis") not in PRIMARY_AUTHORITY_BASES
    ):
        blockers.append("PRIMARY_AUTHORITY_NOT_PROVEN")
    if record.get("candidate_kind") not in CANDIDATE_KINDS:
        blockers.append("INVALID_CANDIDATE_KIND")
    if record.get("pii_status") != "CLEAR":
        blockers.append("PII_NOT_CLEAR")
    if record.get("rights_status") != "CLEARED":
        blockers.append("RIGHTS_NOT_CLEARED")
    if not _SHA256_RE.fullmatch(str(record.get("source_sha256", ""))):
        blockers.append("INVALID_SOURCE_SHA256")
    if not str(record.get("candidate_id", "")).strip():
        blockers.append("INVALID_CANDIDATE_ID")
    if not _SOURCE_DOCUMENT_ID_RE.fullmatch(
        str(record.get("source_document_id", ""))
    ):
        blockers.append("INVALID_SOURCE_DOCUMENT_ID")
    elif _SHA256_RE.fullmatch(str(record.get("source_sha256", ""))):
        expected_source_id = (
            "SRC-" + str(record["source_sha256"])[:16].upper()
        )
        if record["source_document_id"] != expected_source_id:
            blockers.append("SOURCE_ID_HASH_MISMATCH")
    if not str(record.get("candidate_label", "")).strip():
        blockers.append("EMPTY_CANDIDATE_LABEL")

    anchors = record.get("anchor_card_ids")
    if not isinstance(anchors, list) or any(
        not isinstance(item, str) or not _CARD_ID_RE.fullmatch(item) for item in anchors
    ):
        blockers.append("INVALID_ANCHOR_CARD_IDS")

    evidence = record.get("evidence_refs")
    if not isinstance(evidence, list) or not evidence:
        blockers.append("MISSING_EVIDENCE")
    else:
        for item in evidence:
            if not isinstance(item, Mapping):
                blockers.append("INVALID_EVIDENCE_REFERENCE")
                break
            required = {"chunk_id", "source_location", "evidence_hash"}
            if not required.issubset(item):
                blockers.append("INVALID_EVIDENCE_REFERENCE")
                break
            if not _SHA256_RE.fullmatch(str(item.get("evidence_hash", ""))):
                blockers.append("INVALID_EVIDENCE_HASH")
                break
    return blockers


def _validate_source_link(
    candidate: Mapping[str, Any],
    *,
    source_record: Mapping[str, Any] | None,
    require_source_registry: bool,
) -> list[str]:
    if not require_source_registry:
        return []
    if source_record is None:
        return ["SOURCE_NOT_IN_REGISTRY"]

    blockers: list[str] = []
    comparisons = {
        "sha256": ("source_sha256", "SOURCE_REGISTRY_HASH_MISMATCH"),
        "source_authority": (
            "source_authority",
            "SOURCE_REGISTRY_AUTHORITY_MISMATCH",
        ),
        "source_authority_basis": (
            "source_authority_basis",
            "SOURCE_REGISTRY_BASIS_MISMATCH",
        ),
    }
    for source_field, (candidate_field, reason) in comparisons.items():
        if source_record.get(source_field) != candidate.get(candidate_field):
            blockers.append(reason)

    if source_record.get("pii_status") != "CLEAR":
        blockers.append("SOURCE_REGISTRY_PII_NOT_CLEAR")
    if source_record.get("rights_status") != "CLEARED":
        blockers.append("SOURCE_REGISTRY_RIGHTS_NOT_CLEARED")
    if source_record.get("pipeline_status") not in SOURCE_HANDOFF_PIPELINE_STATUSES:
        blockers.append("SOURCE_PIPELINE_NOT_COMPLETE")
    return blockers


def read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with Path(path).open("r", encoding="utf-8-sig") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError as exc:
                raise IntakeContractError(
                    f"Invalid JSON on line {line_number} of {path}: {exc.msg}"
                ) from exc
            if not isinstance(value, dict):
                raise IntakeContractError(
                    f"Line {line_number} of {path} must contain a JSON object"
                )
            yield value


def route_file(
    input_path: Path,
    output_dir: Path,
    source_registry_path: Path,
    *,
    package_id: str | None = None,
    generated_at: str | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    candidates = list(read_jsonl(input_path))
    registry_rows = list(read_jsonl(source_registry_path))
    registry_by_id: dict[str, dict[str, Any]] = {}
    duplicate_registry_ids: set[str] = set()
    for source in registry_rows:
        source_id = str(source.get("source_document_id", ""))
        if source_id in registry_by_id:
            duplicate_registry_ids.add(source_id)
        else:
            registry_by_id[source_id] = source

    candidate_id_counts = Counter(
        str(item.get("candidate_id", "")) for item in candidates
    )
    duplicate_candidate_ids = {
        candidate_id
        for candidate_id, count in candidate_id_counts.items()
        if candidate_id and count > 1
    }

    routed = []
    for item in candidates:
        source_id = str(item.get("source_document_id", ""))
        package_errors = (
            ["DUPLICATE_SOURCE_REGISTRY_ID"]
            if source_id in duplicate_registry_ids
            else []
        )
        if str(item.get("candidate_id", "")) in duplicate_candidate_ids:
            package_errors.append("DUPLICATE_CANDIDATE_ID")
        routed.append(
            route_candidate(
                item,
                source_record=registry_by_id.get(source_id),
                require_source_registry=True,
                registry_errors=package_errors,
            )
        )

    destinations = {
        ROUTE_CANONICAL: output_dir / "canonical_candidates.jsonl",
        ROUTE_SUPPLEMENTAL: output_dir / "supplemental_candidates.jsonl",
        ROUTE_QUARANTINE: output_dir / "quarantine.jsonl",
    }
    for route, path in destinations.items():
        rows = [item for item in routed if item["route"] == route]
        with path.open("w", encoding="utf-8", newline="\n") as target:
            for row in rows:
                output_row = (
                    _quarantine_receipt(row)
                    if route == ROUTE_QUARANTINE
                    else row
                )
                target.write(
                    json.dumps(output_row, ensure_ascii=False, sort_keys=True) + "\n"
                )

    used_source_ids = {
        str(item.get("source_document_id", "")) for item in candidates
    }
    registry_subset = [
        source
        for source in registry_rows
        if str(source.get("source_document_id", "")) in used_source_ids
    ]
    registry_output = output_dir / "source_registry.jsonl"
    with registry_output.open("w", encoding="utf-8", newline="\n") as target:
        for source in sorted(
            registry_subset, key=lambda item: str(item.get("source_document_id", ""))
        ):
            target.write(
                json.dumps(source, ensure_ascii=False, sort_keys=True) + "\n"
            )

    counts = Counter(item["route"] for item in routed)
    report = {
        "input_count": len(routed),
        "route_counts": {route: counts.get(route, 0) for route in destinations},
        "automatic_promotions": 0,
        "neo4j_writes": 0,
    }
    report_path = output_dir / "routing_report.json"
    with report_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as target:
        json.dump(report, target, ensure_ascii=False, indent=2, sort_keys=True)
        target.write("\n")

    artifact_paths = {
        "source_registry.jsonl": registry_output,
        "canonical_candidates.jsonl": destinations[ROUTE_CANONICAL],
        "supplemental_candidates.jsonl": destinations[ROUTE_SUPPLEMENTAL],
        "quarantine.jsonl": destinations[ROUTE_QUARANTINE],
        "routing_report.json": report_path,
    }
    artifacts = {
        name: {
            "sha256": sha256_file(path),
            "record_count": _artifact_record_count(path),
        }
        for name, path in artifact_paths.items()
    }
    derived_package_hash = hashlib.sha256(
        "".join(
            f"{name}:{value['sha256']}\n"
            for name, value in sorted(artifacts.items())
        ).encode("utf-8")
    ).hexdigest()
    resolved_package_id = package_id or f"PKG-{derived_package_hash[:16].upper()}"
    all_sources_present = used_source_ids.issubset(registry_by_id)
    manifest_status = (
        "READY_FOR_DICTIONARY_VALIDATION"
        if all_sources_present and not duplicate_registry_ids
        else "BLOCKED_BY_SOURCE_REGISTRY"
    )
    manifest = {
        "schema_version": "0.1",
        "package_id": resolved_package_id,
        "generated_at": generated_at
        or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "status": manifest_status,
        "input_candidate_count": len(candidates),
        "source_document_ids": sorted(used_source_ids),
        "artifacts": artifacts,
        "contract_artifacts": _contract_artifact_hashes(),
        "route_counts": report["route_counts"],
        "automatic_promotions": 0,
        "neo4j_writes": 0,
    }
    manifest_path = output_dir / "intake_package_manifest.json"
    with manifest_path.open("w", encoding="utf-8", newline="\n") as target:
        json.dump(manifest, target, ensure_ascii=False, indent=2, sort_keys=True)
        target.write("\n")

    report["package_id"] = resolved_package_id
    report["package_status"] = manifest_status
    return report


def _quarantine_receipt(record: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "candidate_id",
        "source_document_id",
        "source_sha256",
        "source_authority",
        "source_authority_basis",
        "candidate_kind",
        "anchor_card_ids",
        "pii_status",
        "rights_status",
        "route",
        "review_status",
        "blocking_reasons",
    }
    return {key: record.get(key) for key in sorted(allowed)}


def _artifact_record_count(path: Path) -> int | None:
    if path.suffix == ".jsonl":
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line)
    return None


def _contract_artifact_hashes() -> dict[str, str]:
    root = Path(__file__).resolve().parent
    paths = {
        "material_intake_router.py": root / "material_intake_router.py",
        "source_registry.schema.json": (
            root / "data" / "material_intake" / "source_registry.schema.json"
        ),
        "candidate_input.schema.json": (
            root / "data" / "material_intake" / "candidate_input.schema.json"
        ),
        "dictionary_handoff.schema.json": (
            root / "data" / "material_intake" / "dictionary_handoff.schema.json"
        ),
        "quarantine_receipt.schema.json": (
            root / "data" / "material_intake" / "quarantine_receipt.schema.json"
        ),
        "intake_package_manifest.schema.json": (
            root
            / "data"
            / "material_intake"
            / "intake_package_manifest.schema.json"
        ),
        "MATERIAL_INTAKE_AND_DICTIONARY_FEEDBACK.md": (
            root
            / "docs"
            / "orchestration"
            / "MATERIAL_INTAKE_AND_DICTIONARY_FEEDBACK.md"
        ),
    }
    return {name: sha256_file(path) for name, path in paths.items()}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    register = subparsers.add_parser("register", help="Register one source file")
    register.add_argument("path", type=Path)
    register.add_argument("--authority", required=True, choices=sorted(SOURCE_AUTHORITIES))
    register.add_argument("--source-type", required=True, choices=sorted(SOURCE_TYPES))
    register.add_argument("--basis", required=True, choices=sorted(SOURCE_AUTHORITY_BASES))
    register.add_argument("--declared-by", required=True)
    register.add_argument(
        "--registry",
        type=Path,
        default=Path("data/material_intake/source_registry.jsonl"),
    )

    route = subparsers.add_parser("route", help="Route a candidate JSONL package")
    route.add_argument("input", type=Path)
    route.add_argument("output_dir", type=Path)
    route.add_argument("--source-registry", type=Path, required=True)
    route.add_argument("--package-id")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.command == "register":
        record = build_source_record(
            args.path,
            source_authority=args.authority,
            source_type=args.source_type,
            authority_basis=args.basis,
            declared_by=args.declared_by,
        )
        created = append_source_record(args.registry, record)
        print(json.dumps({"created": created, "record": record}, ensure_ascii=False))
        return 0

    report = route_file(
        args.input,
        args.output_dir,
        args.source_registry,
        package_id=args.package_id,
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
