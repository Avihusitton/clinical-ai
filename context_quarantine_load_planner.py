# -*- coding: utf-8 -*-
"""Build a write-free Neo4j plan for quarantined context candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from dictionary_release_acceptance import sha256_file


class ContextPlanBlocked(RuntimeError):
    """Raised when quarantine artifacts or dictionary endpoints are invalid."""


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


def _jsonl_bytes(rows: list[dict[str, Any]]) -> bytes:
    return (
        (
            "\n".join(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                for row in rows
            )
            + "\n"
        )
        if rows
        else ""
    ).encode("utf-8")


def _find_dictionary_nodes(plan_dir: Path) -> Path:
    paths = sorted(plan_dir.glob("dictionary_nodes*.jsonl"))
    if len(paths) != 1:
        raise ContextPlanBlocked(
            f"dictionary_nodes_artifact_count:{len(paths)}"
        )
    return paths[0]


def _verify_package(
    package_dir: Path,
) -> tuple[dict[str, Any], list[dict], list[dict]]:
    manifest_path = package_dir / "context_quarantine_manifest.json"
    if not manifest_path.is_file():
        raise ContextPlanBlocked("context_manifest_missing")
    manifest = _read_json(manifest_path)
    if manifest.get("manifest_status") != (
        "CANONICAL_CONTEXT_QUARANTINE_EXPORT"
    ):
        raise ContextPlanBlocked("context_manifest_not_canonical")
    controls = manifest.get("controls", {})
    if (
        controls.get("canonical_semantic_relations") != 0
        or controls.get("automatic_promotions") != 0
        or controls.get("neo4j_writes") != 0
    ):
        raise ContextPlanBlocked("context_safety_controls_failed")
    artifacts = manifest.get("artifacts", {})
    for name, expected in artifacts.items():
        path = package_dir / name
        if (
            not path.is_file()
            or sha256_file(path) != expected.get("sha256")
            or path.stat().st_size != expected.get("bytes")
        ):
            raise ContextPlanBlocked(f"{name}:integrity_failure")
        if len(_read_jsonl(path)) != expected.get("record_count"):
            raise ContextPlanBlocked(f"{name}:count_failure")
    excerpts = _read_jsonl(
        package_dir / "context_evidence_excerpts.jsonl"
    )
    candidates = _read_jsonl(
        package_dir / "clinical_context_relation_candidates.jsonl"
    )
    return manifest, excerpts, candidates


def build_context_quarantine_plan(
    package_dir: Path,
    dictionary_plan_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Create candidate/evidence nodes, never canonical semantic edges."""
    package_dir = Path(package_dir).resolve()
    dictionary_plan_dir = Path(dictionary_plan_dir).resolve()
    output_dir = Path(output_dir).resolve()
    manifest, excerpts, candidates = _verify_package(package_dir)
    dictionary_nodes_path = _find_dictionary_nodes(
        dictionary_plan_dir
    )
    dictionary_nodes = _read_jsonl(dictionary_nodes_path)
    active_card_ids = {
        str(row.get("properties", {}).get("card_id"))
        for row in dictionary_nodes
        if "GlossaryEntry" in row.get("labels", [])
        and row.get("properties", {}).get("status") == "APPROVED"
    }
    mapped_ids = {
        str(card_id)
        for row in candidates
        for key in ("source_card_ids", "target_card_ids")
        for card_id in row.get(key, [])
    }
    missing_cards = sorted(mapped_ids - active_card_ids)
    if missing_cards:
        raise ContextPlanBlocked(
            "mapped_card_ids_missing:" + ",".join(missing_cards)
        )

    nodes = [
        {
            "node_key": f"ChunkEvidenceExcerpt:{row['evidence_id']}",
            "labels": ["ChunkEvidenceExcerpt", "QuarantinedEvidence"],
            "properties": row,
        }
        for row in excerpts
    ]
    nodes.extend(
        {
            "node_key": (
                f"ClinicalContextRelationCandidate:{row['candidate_id']}"
            ),
            "labels": [
                "ClinicalContextRelationCandidate",
                "QuarantinedCandidate",
            ],
            "properties": row,
        }
        for row in candidates
    )
    edges: list[dict[str, Any]] = []
    for row in candidates:
        candidate_key = (
            f"ClinicalContextRelationCandidate:{row['candidate_id']}"
        )
        evidence_key = (
            f"ChunkEvidenceExcerpt:{row['evidence_id']}"
        )
        edges.append(
            {
                "edge_id": (
                    f"QEDGE-{row['candidate_id']}-EVIDENCE"
                ),
                "source_node_key": candidate_key,
                "target_node_key": evidence_key,
                "relation_type": "SUPPORTED_BY_EXCERPT",
                "properties": {
                    "review_status": row["quarantine_status"],
                    "automatic_promotion": False,
                },
            }
        )
        for role, ids in (
            ("CANDIDATE_SOURCE_ENDPOINT", row["source_card_ids"]),
            ("CANDIDATE_TARGET_ENDPOINT", row["target_card_ids"]),
        ):
            for card_id in ids:
                edges.append(
                    {
                        "edge_id": (
                            f"QEDGE-{row['candidate_id']}-{role}-"
                            f"{card_id}"
                        ),
                        "source_node_key": candidate_key,
                        "target_node_key": f"GlossaryEntry:{card_id}",
                        "relation_type": role,
                        "properties": {
                            "review_status": row[
                                "quarantine_status"
                            ],
                            "automatic_promotion": False,
                        },
                    }
                )

    nodes.sort(key=lambda row: row["node_key"])
    edges.sort(key=lambda row: row["edge_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "context_quarantine_nodes.jsonl"
    edges_path = output_dir / "context_quarantine_edges.jsonl"
    nodes_path.write_bytes(_jsonl_bytes(nodes))
    edges_path.write_bytes(_jsonl_bytes(edges))
    seed = (
        f"{manifest['release_id']}|{sha256_file(nodes_path)}|"
        f"{sha256_file(edges_path)}"
    ).encode("utf-8")
    plan_id = (
        "CONTEXTPLAN-"
        + hashlib.sha256(seed).hexdigest()[:16].upper()
    )
    plan_manifest = {
        "schema_version": "0.1",
        "status": "PASS_WRITE_FREE_CONTEXT_QUARANTINE_PLAN",
        "plan_id": plan_id,
        "source_quarantine_release_id": manifest["release_id"],
        "dictionary_release_id": manifest["dictionary_release_id"],
        "counts": {
            "quarantine_nodes": len(nodes),
            "quarantine_edges": len(edges),
            "canonical_semantic_edges": 0,
            "relation_candidates": len(candidates),
            "evidence_excerpts": len(excerpts),
        },
        "artifacts": {
            nodes_path.name: {
                "sha256": sha256_file(nodes_path),
                "bytes": nodes_path.stat().st_size,
                "record_count": len(nodes),
            },
            edges_path.name: {
                "sha256": sha256_file(edges_path),
                "bytes": edges_path.stat().st_size,
                "record_count": len(edges),
            },
        },
        "controls": {
            "dictionary_card_id_endpoints_verified": True,
            "chunk_nodes_impersonated": 0,
            "canonical_semantic_edges": 0,
            "automatic_promotions": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        },
        "required_load_predecessor": (
            f"DICTIONARY_RELEASE:{manifest['dictionary_release_id']}"
        ),
        "eligible_for_staging_quarantine_load": True,
        "eligible_for_canonical_relation_load": False,
        "eligible_for_production_execution": False,
    }
    manifest_path = (
        output_dir / "context_quarantine_graph_plan_manifest.json"
    )
    manifest_path.write_text(
        json.dumps(plan_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return plan_manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument("--dictionary-plan", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_context_quarantine_plan(
            args.package_dir,
            args.dictionary_plan,
            args.output_dir,
        )
    except ContextPlanBlocked as error:
        report = {
            "status": "BLOCKED_CONTEXT_QUARANTINE_PLAN",
            "error": str(error),
            "automatic_promotions": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
