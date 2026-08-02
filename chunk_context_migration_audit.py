# -*- coding: utf-8 -*-
"""Audit legacy chunk context for migration to dictionary card identifiers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from dictionary_release_acceptance import sha256_file


AUDIT_VERSION = "0.1"


class ChunkAuditRejected(RuntimeError):
    """Raised when required audit inputs are malformed or missing."""


def _read_json(path: Path) -> Any:
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
            raise ChunkAuditRejected(
                f"{path.name}:{line_number}:invalid_json"
            ) from error
        if not isinstance(row, dict):
            raise ChunkAuditRejected(
                f"{path.name}:{line_number}:record_not_object"
            )
        rows.append(row)
    return rows


def _normalize_term(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(
        character
        for character in value
        if not unicodedata.category(character).startswith("M")
    )
    value = unicodedata.normalize("NFKC", value)
    value = value.replace("־", " ").replace("-", " ")
    value = re.sub(r"[^\w\u0590-\u05ff]+", " ", value)
    return " ".join(value.split())


def _find_graph_artifact(plan_dir: Path, prefix: str) -> Path:
    paths = sorted(plan_dir.glob(f"{prefix}*.jsonl"))
    if len(paths) != 1:
        raise ChunkAuditRejected(
            f"{prefix}:artifact_count:{len(paths)}"
        )
    return paths[0]


def _find_graph_manifest(plan_dir: Path) -> Path:
    paths = sorted(
        plan_dir.glob("dictionary_graph_plan_manifest*.json")
    )
    if len(paths) != 1:
        raise ChunkAuditRejected(
            f"graph_plan_manifest_count:{len(paths)}"
        )
    return paths[0]


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    lines = [
        json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for row in rows
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode(
        "utf-8"
    )


def _candidate_id(row: dict[str, Any], row_number: int) -> str:
    seed = "|".join(
        [
            str(row_number),
            str(row.get("chunk_id", "")),
            str(row.get("concept_a", "")),
            str(row.get("type", "")),
            str(row.get("concept_b", "")),
        ]
    ).encode("utf-8")
    return "CHUNKCAND-" + hashlib.sha256(seed).hexdigest()[:20].upper()


def _build_alias_index(
    nodes: list[dict[str, Any]],
    edges: list[dict[str, Any]],
) -> tuple[dict[str, set[str]], set[str]]:
    alias_index: dict[str, set[str]] = defaultdict(set)
    active_card_ids: set[str] = set()
    nodes_by_key = {
        str(node.get("node_key")): node
        for node in nodes
        if node.get("node_key")
    }
    for node in nodes:
        if "GlossaryEntry" not in node.get("labels", []):
            continue
        properties = node.get("properties", {})
        card_id = str(properties.get("card_id", ""))
        if properties.get("status") not in {"APPROVED", "DRAFT"}:
            continue
        active_card_ids.add(card_id)
        terms = [properties.get("entry_name", "")]
        terms.extend(properties.get("aliases_and_spellings", []))
        for term in terms:
            normalized = _normalize_term(str(term))
            if normalized:
                alias_index[normalized].add(card_id)

    redirect_targets = {
        str(row.get("source_node_key")): str(
            row.get("target_node_key")
        )
        for row in edges
        if row.get("relation_type") == "REDIRECTS_TO"
    }
    for source_key, target_key in redirect_targets.items():
        source_node = nodes_by_key.get(source_key, {})
        target_node = nodes_by_key.get(target_key, {})
        source_properties = source_node.get("properties", {})
        target_card_id = str(
            target_node.get("properties", {}).get("card_id", "")
        )
        if (
            "DictionaryRedirect" not in source_node.get("labels", [])
            or source_properties.get("status") != "DEPRECATED"
            or target_card_id not in active_card_ids
        ):
            continue
        terms = [source_properties.get("entry_name", "")]
        terms.extend(source_properties.get("aliases_and_spellings", []))
        for term in terms:
            normalized = _normalize_term(str(term))
            if normalized:
                alias_index[normalized].add(target_card_id)
    return alias_index, active_card_ids


def _map_term(
    value: str,
    alias_index: dict[str, set[str]],
) -> tuple[str, list[str]]:
    matches = sorted(alias_index.get(_normalize_term(value), set()))
    if len(matches) == 1:
        return "UNIQUE", matches
    if len(matches) > 1:
        return "AMBIGUOUS", matches
    return "UNMAPPED", []


def create_chunk_context_audit(
    plan_dir: Path,
    queue_path: Path,
    baseline_path: Path,
    linking_stats_path: Path,
    chunk_manifest_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Create a write-free migration audit and quarantined candidate export."""
    plan_dir = Path(plan_dir).resolve()
    output_dir = Path(output_dir).resolve()
    graph_manifest_path = _find_graph_manifest(plan_dir)
    graph_manifest = _read_json(graph_manifest_path)
    nodes_path = _find_graph_artifact(plan_dir, "dictionary_nodes")
    edges_path = _find_graph_artifact(plan_dir, "dictionary_edges")
    nodes = _read_jsonl(nodes_path)
    edges = _read_jsonl(edges_path)
    alias_index, active_card_ids = _build_alias_index(nodes, edges)

    queue = _read_json(Path(queue_path).resolve())
    baseline = _read_json(Path(baseline_path).resolve())
    linking_stats = _read_json(Path(linking_stats_path).resolve())
    chunk_manifest = _read_json(Path(chunk_manifest_path).resolve())
    if not isinstance(queue, list):
        raise ChunkAuditRejected("queue_not_array")

    candidate_rows: list[dict[str, Any]] = []
    mapping_counts: Counter[str] = Counter()
    relation_counts: Counter[str] = Counter()
    status_counts: Counter[str] = Counter()
    chunk_ids: set[str] = set()
    for row_number, row in enumerate(queue, start=1):
        if not isinstance(row, dict):
            raise ChunkAuditRejected(
                f"queue:{row_number}:record_not_object"
            )
        status_a, matches_a = _map_term(
            str(row.get("concept_a", "")),
            alias_index,
        )
        status_b, matches_b = _map_term(
            str(row.get("concept_b", "")),
            alias_index,
        )
        pair_status = (
            "BOTH_UNIQUE"
            if status_a == status_b == "UNIQUE"
            else "AMBIGUOUS"
            if "AMBIGUOUS" in {status_a, status_b}
            else "UNMAPPED"
        )
        mapping_counts[pair_status] += 1
        relation_counts[str(row.get("type", ""))] += 1
        status_counts[str(row.get("status", ""))] += 1
        if row.get("chunk_id"):
            chunk_ids.add(str(row["chunk_id"]))
        quote = str(row.get("quote", ""))
        candidate_rows.append(
            {
                "candidate_id": _candidate_id(row, row_number),
                "source_row_number": row_number,
                "chunk_id": row.get("chunk_id"),
                "relation_type": row.get("type"),
                "concept_a_legacy_name": row.get("concept_a"),
                "concept_b_legacy_name": row.get("concept_b"),
                "concept_a_mapping_status": status_a,
                "concept_a_card_ids": matches_a,
                "concept_b_mapping_status": status_b,
                "concept_b_card_ids": matches_b,
                "pair_mapping_status": pair_status,
                "source_review_status": row.get("status"),
                "evidence_quote_sha256": (
                    hashlib.sha256(quote.encode("utf-8")).hexdigest()
                    if quote
                    else None
                ),
                "automatic_promotion": False,
                "eligible_for_load": False,
            }
        )

    candidate_rows.sort(key=lambda row: row["candidate_id"])
    preview = bool(graph_manifest.get("preview"))
    candidate_filename = (
        "chunk_relation_candidates.preview.jsonl"
        if preview
        else "chunk_relation_candidates.jsonl"
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    candidate_path = output_dir / candidate_filename
    candidate_path.write_bytes(_jsonl_bytes(candidate_rows))

    graph_relationships = baseline.get("relationships", {})
    legacy_relationship_count = sum(
        int(value)
        for value in graph_relationships.values()
        if isinstance(value, int)
    )
    files = chunk_manifest.get("files", [])
    durable_chunk_records = 0
    if isinstance(files, list):
        durable_chunk_records = sum(
            int(row.get("n_chunks", 0))
            for row in files
            if isinstance(row, dict)
        )

    blockers = [
        "CANONICAL_DICTIONARY_RELEASE_REQUIRED"
        if preview
        else None,
        "FULL_DURABLE_CHUNK_EXPORT_REQUIRED",
        "LEGACY_GRAPH_ENDPOINT_EXPORT_REQUIRED",
        "PENDING_CONTEXT_RELATIONS_REQUIRE_REVIEW",
        "CARD_ID_REMAP_REQUIRED",
        "NONPRODUCTION_TARGET_VERIFICATION_REQUIRED",
    ]
    blockers = [item for item in blockers if item]

    seed = (
        f"{AUDIT_VERSION}|{graph_manifest['plan_id']}|"
        f"{sha256_file(Path(queue_path).resolve())}|"
        f"{sha256_file(candidate_path)}"
    ).encode("utf-8")
    audit_id = (
        "CHUNKAUDIT-" + hashlib.sha256(seed).hexdigest()[:16].upper()
    )
    report = {
        "schema_version": "0.1",
        "audit_version": AUDIT_VERSION,
        "status": "PASS_WRITE_FREE_CHUNK_CONTEXT_AUDIT",
        "audit_id": audit_id,
        "source_plan_id": graph_manifest["plan_id"],
        "source_release_id": graph_manifest["source_release_id"],
        "preview": preview,
        "dictionary": {
            "active_or_draft_card_ids": len(active_card_ids),
            "normalized_alias_keys": len(alias_index),
        },
        "legacy_inventory": {
            "baseline_nodes": baseline.get("nodes", {}),
            "baseline_relationships": graph_relationships,
            "baseline_relationship_total": legacy_relationship_count,
            "linking_stats": linking_stats,
            "manifest_chunk_records": durable_chunk_records,
            "queued_relation_candidates": len(queue),
            "queued_unique_chunk_ids": len(chunk_ids),
            "queue_status_counts": dict(sorted(status_counts.items())),
            "queue_relation_type_counts": dict(
                sorted(relation_counts.items())
            ),
        },
        "mapping": {
            "both_endpoints_unique": mapping_counts["BOTH_UNIQUE"],
            "ambiguous": mapping_counts["AMBIGUOUS"],
            "unmapped": mapping_counts["UNMAPPED"],
            "automatically_promoted": 0,
            "eligible_for_load": 0,
        },
        "candidate_artifact": {
            "path": str(candidate_path),
            "sha256": sha256_file(candidate_path),
            "record_count": len(candidate_rows),
        },
        "required_load_order": [
            "CANONICAL_DICTIONARY_NODES_AND_EDGES",
            "CHUNK_NODES",
            "DETERMINISTIC_HAS_CANDIDATE_REBUILT_AGAINST_CARD_ID",
            "REVALIDATED_LINKED_TO",
            "REVIEWED_CONTEXT_RELATIONS",
        ],
        "controls": {
            "legacy_names_are_not_graph_identity": True,
            "dictionary_card_id_is_graph_identity": True,
            "pending_queue_is_quarantined": True,
            "old_linked_to_is_not_automatically_promoted": True,
            "evidence_quotes_copied_to_generated_artifact": False,
            "neo4j_connections": 0,
            "neo4j_reads": 0,
            "neo4j_writes": 0,
        },
        "blockers_for_chunk_context_load": blockers,
        "eligible_for_chunk_context_load": False,
        "eligible_for_production_execution": False,
    }
    marker = ".preview" if preview else ""
    report_path = (
        output_dir / f"chunk_context_migration_audit{marker}.json"
    )
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-dir", required=True, type=Path)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--baseline", required=True, type=Path)
    parser.add_argument("--linking-stats", required=True, type=Path)
    parser.add_argument("--chunk-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = create_chunk_context_audit(
            args.plan_dir,
            args.queue,
            args.baseline,
            args.linking_stats,
            args.chunk_manifest,
            args.output_dir,
        )
    except ChunkAuditRejected as error:
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
