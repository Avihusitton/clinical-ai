# -*- coding: utf-8 -*-
"""Create a deterministic, write-free graph plan from a dictionary package."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable

from dictionary_release_acceptance import (
    ROLE_FILENAMES,
    read_csv_rows,
    read_jsonl,
    sha256_file,
    validate_package,
)


ADAPTER_VERSION = "0.1"


class PackageRejected(RuntimeError):
    """Raised when a dictionary package fails independent acceptance."""


def _resolve_role_path(package_dir: Path, role: str) -> Path:
    for filename in ROLE_FILENAMES[role]:
        path = package_dir / filename
        if path.is_file():
            return path
    raise PackageRejected(f"Required role is missing: {role}")


def _jsonl_bytes(rows: Iterable[dict[str, Any]]) -> bytes:
    lines = [
        json.dumps(
            row,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        for row in rows
    ]
    return (("\n".join(lines) + "\n") if lines else "").encode("utf-8")


def _edge_id(*parts: str) -> str:
    encoded = "\x1f".join(parts).encode("utf-8")
    return "EDGE-" + hashlib.sha256(encoded).hexdigest()[:20].upper()


def _labels_for_record(record: dict[str, Any]) -> list[str]:
    if record["status"] == "DEPRECATED":
        return ["GlossaryEntry", "DictionaryRedirect"]
    if record["entry_type"] == "EXERCISE":
        return ["GlossaryEntry", "Exercise"]
    return ["GlossaryEntry", "Concept"]


def _glossary_node_key(card_id: str) -> str:
    return f"GlossaryEntry:{card_id}"


def _source_node_key(source_document_id: str) -> str:
    return f"SourceDocument:{source_document_id}"


def build_graph_plan(
    package_dir: Path,
    schema_path: Path,
    output_dir: Path,
) -> dict[str, Any]:
    package_dir = Path(package_dir).resolve()
    schema_path = Path(schema_path).resolve()
    output_dir = Path(output_dir).resolve()

    acceptance = validate_package(package_dir, schema_path)
    if not str(acceptance.get("status", "")).startswith("PASS_"):
        raise PackageRejected(
            "Dictionary package failed acceptance: "
            + "; ".join(acceptance.get("errors", []))
        )

    manifest_path = Path(acceptance["manifest_path"])
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    is_preview = (
        manifest.get("manifest_status")
        == "PREVIEW_NOT_A_CANONICAL_RELEASE"
    )
    filename_marker = ".preview" if is_preview else ""

    glossary_path = _resolve_role_path(package_dir, "glossary")
    redirects_path = _resolve_role_path(package_dir, "redirects")
    cross_path = _resolve_role_path(package_dir, "cross_references")
    source_path = _resolve_role_path(package_dir, "source_map")
    candidates_path = _resolve_role_path(package_dir, "relation_candidates")

    glossary_records = read_jsonl(glossary_path)
    redirect_rows = read_csv_rows(redirects_path)[1]
    cross_rows = read_csv_rows(cross_path)[1]
    source_rows = read_csv_rows(source_path)[1]
    candidate_rows = read_csv_rows(candidates_path)[1]

    nodes: list[dict[str, Any]] = []
    for record in sorted(glossary_records, key=lambda row: row["card_id"]):
        nodes.append(
            {
                "node_key": _glossary_node_key(record["card_id"]),
                "labels": _labels_for_record(record),
                "identity_property": "card_id",
                "identity_value": record["card_id"],
                "properties": record,
            }
        )

    source_by_id: dict[str, dict[str, str]] = {}
    for row in source_rows:
        source_by_id.setdefault(row["source_document_id"], row)
    for source_id in sorted(source_by_id):
        row = source_by_id[source_id]
        nodes.append(
            {
                "node_key": _source_node_key(source_id),
                "labels": ["SourceDocument"],
                "identity_property": "source_document_id",
                "identity_value": source_id,
                "properties": {
                    "source_document_id": source_id,
                    "source_sha256": row["source_sha256"],
                    "source_type": row["source_type"],
                    "source_authority": row["source_authority"],
                },
            }
        )

    edges: list[dict[str, Any]] = []
    for row in cross_rows:
        edge_id = _edge_id(
            row["source_card_id"],
            row["relation_type"],
            row["target_card_id"],
            row["source_document_id"],
            row["evidence_locator"],
        )
        edges.append(
            {
                "edge_id": edge_id,
                "source_node_key": _glossary_node_key(
                    row["source_card_id"]
                ),
                "target_node_key": _glossary_node_key(
                    row["target_card_id"]
                ),
                "relation_type": row["relation_type"],
                "properties": {
                    "directionality": row["directionality"],
                    "certainty": row["certainty"],
                    "review_status": row["review_status"],
                    "source_document_id": row["source_document_id"],
                    "evidence_locator": row["evidence_locator"],
                    "dictionary_release_id": manifest["release_id"],
                },
            }
        )

    for row in redirect_rows:
        edge_id = _edge_id(
            row["source_id"],
            "REDIRECTS_TO",
            row["target_id"],
            manifest["release_id"],
        )
        edges.append(
            {
                "edge_id": edge_id,
                "source_node_key": _glossary_node_key(row["source_id"]),
                "target_node_key": _glossary_node_key(row["target_id"]),
                "relation_type": "REDIRECTS_TO",
                "properties": {
                    "redirect_type": row["redirect_type"],
                    "review_status": "APPROVED_DICTIONARY",
                    "dictionary_release_id": manifest["release_id"],
                },
            }
        )

    for row in source_rows:
        edge_id = _edge_id(
            row["card_id"],
            "EVIDENCED_BY",
            row["source_document_id"],
            row["evidence_locator"],
            row["evidence_type"],
        )
        edges.append(
            {
                "edge_id": edge_id,
                "source_node_key": _glossary_node_key(row["card_id"]),
                "target_node_key": _source_node_key(
                    row["source_document_id"]
                ),
                "relation_type": "EVIDENCED_BY",
                "properties": {
                    "evidence_locator": row["evidence_locator"],
                    "evidence_type": row["evidence_type"],
                    "certainty": row["certainty"],
                    "source_authority": row["source_authority"],
                    "dictionary_release_id": manifest["release_id"],
                },
            }
        )

    candidate_edges: list[dict[str, Any]] = []
    for row in candidate_rows:
        candidate_edges.append(
            {
                "candidate_edge_id": _edge_id(
                    row["source_card_id"],
                    row["relation_type"],
                    row["target_card_id"],
                    row["source_document_id"],
                    row["evidence_locator"],
                    "CANDIDATE",
                ),
                "source_node_key": _glossary_node_key(
                    row["source_card_id"]
                ),
                "target_node_key": _glossary_node_key(
                    row["target_card_id"]
                ),
                "relation_type": row["relation_type"],
                "directionality": row["directionality"],
                "certainty": row["certainty"],
                "review_status": row["review_status"],
                "source_document_id": row["source_document_id"],
                "evidence_locator": row["evidence_locator"],
                "contradiction_note": row["contradiction_note"],
                "automatic": False,
            }
        )

    nodes.sort(key=lambda row: row["node_key"])
    edges.sort(key=lambda row: row["edge_id"])
    candidate_edges.sort(key=lambda row: row["candidate_edge_id"])

    known_node_keys = {row["node_key"] for row in nodes}
    broken_edges = [
        row["edge_id"]
        for row in edges
        if row["source_node_key"] not in known_node_keys
        or row["target_node_key"] not in known_node_keys
    ]
    broken_candidates = [
        row["candidate_edge_id"]
        for row in candidate_edges
        if row["source_node_key"] not in known_node_keys
        or row["target_node_key"] not in known_node_keys
    ]
    duplicate_node_keys = len(known_node_keys) != len(nodes)
    duplicate_edge_ids = len({row["edge_id"] for row in edges}) != len(edges)
    if broken_edges or broken_candidates or duplicate_node_keys or duplicate_edge_ids:
        raise PackageRejected(
            "Adapter invariant failed: "
            f"broken_edges={len(broken_edges)}, "
            f"broken_candidates={len(broken_candidates)}, "
            f"duplicate_nodes={duplicate_node_keys}, "
            f"duplicate_edges={duplicate_edge_ids}"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / f"dictionary_nodes{filename_marker}.jsonl"
    edges_path = output_dir / f"dictionary_edges{filename_marker}.jsonl"
    candidates_output_path = (
        output_dir
        / f"dictionary_relation_candidates{filename_marker}.jsonl"
    )
    nodes_path.write_bytes(_jsonl_bytes(nodes))
    edges_path.write_bytes(_jsonl_bytes(edges))
    candidates_output_path.write_bytes(_jsonl_bytes(candidate_edges))

    source_manifest_sha = sha256_file(manifest_path)
    plan_seed = (
        f"{ADAPTER_VERSION}|{manifest['release_id']}|{source_manifest_sha}"
    ).encode("utf-8")
    plan_id = "GRAPHPLAN-" + hashlib.sha256(plan_seed).hexdigest()[
        :16
    ].upper()

    artifact_paths = [
        nodes_path,
        edges_path,
        candidates_output_path,
    ]
    plan_manifest = {
        "schema_version": "0.1",
        "adapter_version": ADAPTER_VERSION,
        "plan_id": plan_id,
        "source_release_id": manifest["release_id"],
        "source_manifest_status": manifest["manifest_status"],
        "source_manifest_actual_sha256": source_manifest_sha,
        "source_schema_sha256": acceptance["schema_sha256"],
        "preview": is_preview,
        "counts": {
            "glossary_nodes": len(glossary_records),
            "source_document_nodes": len(source_by_id),
            "total_nodes": len(nodes),
            "approved_dictionary_edges": len(cross_rows),
            "redirect_edges": len(redirect_rows),
            "evidence_edges": len(source_rows),
            "total_edges": len(edges),
            "relation_candidates": len(candidate_edges),
        },
        "artifacts": {
            path.name: {
                "sha256": sha256_file(path),
                "bytes": path.stat().st_size,
                "record_count": (
                    len(nodes)
                    if path == nodes_path
                    else len(edges)
                    if path == edges_path
                    else len(candidate_edges)
                ),
            }
            for path in artifact_paths
        },
        "controls": {
            "source_acceptance_status": acceptance["status"],
            "all_edge_endpoints_exist": True,
            "duplicate_node_keys": 0,
            "duplicate_edge_ids": 0,
            "candidate_edges_in_load_plan": 0,
            "legacy_mapping_created": False,
            "automatic_promotions": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        },
        "eligible_for_write_free_dry_run": True,
        "eligible_for_neo4j_write": False,
    }
    plan_manifest_path = (
        output_dir
        / f"dictionary_graph_plan_manifest{filename_marker}.json"
    )
    plan_manifest_path.write_text(
        json.dumps(plan_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    return {
        "status": "PASS_WRITE_FREE_GRAPH_PLAN_CREATED",
        "plan_id": plan_id,
        "source_acceptance_status": acceptance["status"],
        "manifest_path": str(plan_manifest_path),
        "counts": plan_manifest["counts"],
        "automatic_promotions": 0,
        "neo4j_connections": 0,
        "neo4j_writes": 0,
        "eligible_for_neo4j_write": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("data/official_glossary/schema.json"),
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_graph_plan(
            args.package_dir,
            args.schema,
            args.output_dir,
        )
    except PackageRejected as error:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": str(error),
                    "automatic_promotions": 0,
                    "neo4j_connections": 0,
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
