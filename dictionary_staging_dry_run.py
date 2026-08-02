# -*- coding: utf-8 -*-
"""Validate a dictionary graph plan and create a zero-write staging plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from dictionary_release_acceptance import (
    CANONICAL_MANIFEST_STATUSES,
    sha256_file,
)


DRY_RUN_VERSION = "0.1"
DEFAULT_BATCH_SIZE = 250
RELATION_TYPE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
EMAIL_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+972[- ]?|0)(?:[23489]|5\d)[- ]?\d{3}[- ]?\d{4}(?!\d)"
)
ISRAELI_ID_PATTERN = re.compile(r"(?<!\d)\d{9}(?!\d)")
STRUCTURED_SOURCE_ID_PATTERN = re.compile(r"SRC-[A-F0-9]{16}")
SHA256_TOKEN_PATTERN = re.compile(r"(?<![a-f0-9])[a-f0-9]{64}(?![a-f0-9])")
HUMAN_TEXT_FIELDS = {
    "entry_name",
    "aliases_and_spellings",
    "source_based_definition",
    "unified_definition",
    "short_example",
    "common_mistakes",
    "exact_source",
    "editorial_note",
}


class DryRunRejected(RuntimeError):
    """Raised when a graph plan cannot pass a write-free dry run."""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
            raise DryRunRejected(
                f"{path.name}:{line_number}:invalid_json"
            ) from error
        if not isinstance(row, dict):
            raise DryRunRejected(
                f"{path.name}:{line_number}:record_not_object"
            )
        rows.append(row)
    return rows


def _find_manifest(plan_dir: Path) -> Path:
    paths = sorted(
        plan_dir.glob("dictionary_graph_plan_manifest*.json")
    )
    if len(paths) != 1:
        raise DryRunRejected(
            f"graph_plan_manifest_count:{len(paths)}"
        )
    return paths[0]


def _artifact_path(
    plan_dir: Path,
    manifest: dict[str, Any],
    prefix: str,
) -> Path:
    names = [
        name
        for name in manifest.get("artifacts", {})
        if name.startswith(prefix)
    ]
    if len(names) != 1:
        raise DryRunRejected(
            f"artifact_role:{prefix}:count:{len(names)}"
        )
    return plan_dir / names[0]


def _text_values(properties: dict[str, Any]) -> list[str]:
    values: list[str] = []
    for field in HUMAN_TEXT_FIELDS:
        value = properties.get(field)
        if isinstance(value, str):
            values.append(value)
        elif isinstance(value, list):
            values.extend(item for item in value if isinstance(item, str))
    return values


def _identifier_findings(
    nodes: list[dict[str, Any]],
) -> list[str]:
    findings: list[str] = []
    patterns = (
        ("email", EMAIL_PATTERN),
        ("phone", PHONE_PATTERN),
        ("israeli_id_candidate", ISRAELI_ID_PATTERN),
    )
    for node in nodes:
        if "GlossaryEntry" not in node.get("labels", []):
            continue
        card_id = str(node.get("identity_value", "UNKNOWN"))
        text = "\n".join(_text_values(node.get("properties", {})))
        text = STRUCTURED_SOURCE_ID_PATTERN.sub("", text)
        text = SHA256_TOKEN_PATTERN.sub("", text)
        for label, pattern in patterns:
            if pattern.search(text):
                findings.append(f"{card_id}:{label}")
    return sorted(findings)


def _validate_artifacts(
    plan_dir: Path,
    manifest: dict[str, Any],
) -> dict[str, Path]:
    resolved: dict[str, Path] = {}
    errors: list[str] = []
    for name, expected in manifest.get("artifacts", {}).items():
        path = plan_dir / name
        resolved[name] = path
        if not path.is_file():
            errors.append(f"{name}:missing")
            continue
        if sha256_file(path) != expected.get("sha256"):
            errors.append(f"{name}:sha256_mismatch")
        if path.stat().st_size != expected.get("bytes"):
            errors.append(f"{name}:byte_count_mismatch")
        if len(_read_jsonl(path)) != expected.get("record_count"):
            errors.append(f"{name}:record_count_mismatch")
    if errors:
        raise DryRunRejected(";".join(sorted(errors)))
    return resolved


def create_staging_dry_run(
    plan_dir: Path,
    output_path: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict[str, Any]:
    """Create a deterministic staging dry-run report without a DB connection."""
    plan_dir = Path(plan_dir).resolve()
    output_path = Path(output_path).resolve()
    if batch_size < 1:
        raise DryRunRejected("batch_size_must_be_positive")

    manifest_path = _find_manifest(plan_dir)
    manifest = _read_json(manifest_path)
    _validate_artifacts(plan_dir, manifest)

    nodes_path = _artifact_path(
        plan_dir,
        manifest,
        "dictionary_nodes",
    )
    edges_path = _artifact_path(
        plan_dir,
        manifest,
        "dictionary_edges",
    )
    candidates_path = _artifact_path(
        plan_dir,
        manifest,
        "dictionary_relation_candidates",
    )
    nodes = _read_jsonl(nodes_path)
    edges = _read_jsonl(edges_path)
    candidates = _read_jsonl(candidates_path)

    errors: list[str] = []
    node_keys = [str(row.get("node_key", "")) for row in nodes]
    edge_ids = [str(row.get("edge_id", "")) for row in edges]
    known_node_keys = set(node_keys)
    if len(known_node_keys) != len(node_keys):
        errors.append("duplicate_node_keys")
    if len(set(edge_ids)) != len(edge_ids):
        errors.append("duplicate_edge_ids")

    for row in nodes:
        identity_property = row.get("identity_property")
        identity_value = row.get("identity_value")
        properties = row.get("properties", {})
        if (
            not row.get("node_key")
            or not isinstance(row.get("labels"), list)
            or not row.get("labels")
        ):
            errors.append("invalid_node_shape")
            continue
        if properties.get(identity_property) != identity_value:
            errors.append(
                f"{row['node_key']}:identity_property_mismatch"
            )

    for row in edges:
        edge_id = str(row.get("edge_id", "UNKNOWN"))
        if row.get("source_node_key") not in known_node_keys:
            errors.append(f"{edge_id}:missing_source")
        if row.get("target_node_key") not in known_node_keys:
            errors.append(f"{edge_id}:missing_target")
        if not RELATION_TYPE_PATTERN.fullmatch(
            str(row.get("relation_type", ""))
        ):
            errors.append(f"{edge_id}:invalid_relation_type")
        if row.get("properties", {}).get("review_status") == (
            "PENDING_DICTIONARY_REVIEW"
        ):
            errors.append(f"{edge_id}:candidate_in_load_plan")

    identifier_findings = _identifier_findings(nodes)
    errors.extend(
        f"identifier_screening:{finding}"
        for finding in identifier_findings
    )

    candidate_ids = [
        str(row.get("candidate_edge_id", ""))
        for row in candidates
    ]
    if len(set(candidate_ids)) != len(candidate_ids):
        errors.append("duplicate_candidate_edge_ids")

    node_label_counts: Counter[str] = Counter()
    for row in nodes:
        node_label_counts.update(row.get("labels", []))
    relation_counts = Counter(
        str(row.get("relation_type", "")) for row in edges
    )
    node_batch_count = math.ceil(len(nodes) / batch_size)
    edge_batch_count = math.ceil(len(edges) / batch_size)

    seed = (
        f"{DRY_RUN_VERSION}|{manifest['plan_id']}|"
        f"{sha256_file(manifest_path)}|{batch_size}"
    ).encode("utf-8")
    dry_run_id = (
        "DRYRUN-" + hashlib.sha256(seed).hexdigest()[:16].upper()
    )
    ingestion_batch_id = (
        "DICTBATCH-"
        + hashlib.sha256(
            f"{manifest['source_release_id']}|{manifest['plan_id']}".encode(
                "utf-8"
            )
        ).hexdigest()[:20].upper()
    )

    preview = bool(manifest.get("preview"))
    canonical_release = (
        not preview
        and manifest.get("source_manifest_status")
        in CANONICAL_MANIFEST_STATUSES
    )
    blockers: list[str] = []
    if errors:
        blockers.append("DRY_RUN_VALIDATION_ERRORS")
    if not canonical_release:
        blockers.append("CANONICAL_RELEASE_REQUIRED")
    blockers.extend(
        [
            "NONPRODUCTION_TARGET_VERIFICATION_REQUIRED",
            "PRELOAD_TOUCHED_KEY_SNAPSHOT_REQUIRED",
        ]
    )

    report = {
        "schema_version": "0.1",
        "dry_run_version": DRY_RUN_VERSION,
        "status": (
            "PASS_WRITE_FREE_STAGING_DRY_RUN"
            if not errors
            else "BLOCKED_DRY_RUN_VALIDATION_FAILED"
        ),
        "dry_run_id": dry_run_id,
        "ingestion_batch_id": ingestion_batch_id,
        "source_plan_id": manifest["plan_id"],
        "source_release_id": manifest["source_release_id"],
        "source_manifest_status": manifest[
            "source_manifest_status"
        ],
        "source_plan_manifest_sha256": sha256_file(manifest_path),
        "preview": preview,
        "batch_size": batch_size,
        "counts": {
            "nodes_to_merge": len(nodes),
            "relationships_to_merge": len(edges),
            "relation_candidates_quarantined": len(candidates),
            "records_rejected": len(errors),
            "dry_run_errors": len(errors),
            "estimated_node_batches": node_batch_count,
            "estimated_relationship_batches": edge_batch_count,
        },
        "node_label_counts": dict(sorted(node_label_counts.items())),
        "relationship_type_counts": dict(
            sorted(relation_counts.items())
        ),
        "planned_constraints": [
            {
                "label": "GlossaryEntry",
                "property": "card_id",
                "kind": "UNIQUE",
            },
            {
                "label": "SourceDocument",
                "property": "source_document_id",
                "kind": "UNIQUE",
            },
        ],
        "execution_controls": {
            "candidate_edges_in_load_plan": 0,
            "identifier_screening_findings": len(
                identifier_findings
            ),
            "target_verification": "NOT_RUN",
            "target_must_be_nonproduction": True,
            "preload_touched_key_snapshot": "REQUIRED",
            "rollback_scope": "EXACT_INGESTION_BATCH_ID",
            "post_load_validation": "REQUIRED",
            "neo4j_connections": 0,
            "neo4j_reads": 0,
            "neo4j_writes": 0,
        },
        "rollback_plan": {
            "batch_id": ingestion_batch_id,
            "relationship_identity": "edge_id",
            "node_identity": "node_key",
            "requires_preload_snapshot": True,
            "restore_updated_entities_from_snapshot": True,
            "delete_only_entities_created_by_batch": True,
        },
        "errors": sorted(set(errors)),
        "blockers_for_staging_execution": blockers,
        "eligible_for_staging_execution": False,
        "eligible_for_production_execution": False,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--batch-size",
        type=int,
        default=DEFAULT_BATCH_SIZE,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = create_staging_dry_run(
            args.plan_dir,
            args.output,
            args.batch_size,
        )
    except DryRunRejected as error:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": str(error),
                    "neo4j_connections": 0,
                    "neo4j_reads": 0,
                    "neo4j_writes": 0,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not report["errors"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
