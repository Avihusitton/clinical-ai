# -*- coding: utf-8 -*-
"""Guarded Neo4j staging loader for canonical chunk-to-card context."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from canonical_dictionary_staging_loader import (
    CONSTRAINTS,
    LABEL_PATTERN,
    RELATION_PATTERN,
    StagingLoadBlocked,
    _load_edges,
    _load_nodes,
    _post_load_validation,
    _read_json,
    _read_jsonl,
    _snapshot,
    _write_snapshot,
)
from dictionary_release_acceptance import sha256_file
from neo4j_target_static_audit import _read_env, audit_target_values


CHUNK_CONSTRAINT = (
    "chunk_id_unique",
    "CREATE CONSTRAINT chunk_id_unique "
    "IF NOT EXISTS FOR (n:Chunk) REQUIRE n.chunk_id IS UNIQUE",
)
ALLOWED_CHUNK_RELATIONS = {"HAS_CANDIDATE", "LINKED_TO"}


def load_chunk_plan(plan_dir: Path) -> dict[str, Any]:
    """Read and independently verify a canonical chunk graph plan."""
    plan_dir = Path(plan_dir).resolve()
    manifest_path = plan_dir / "chunk_graph_plan_manifest.json"
    if not manifest_path.is_file():
        raise StagingLoadBlocked("chunk_graph_plan_manifest_missing")
    manifest = _read_json(manifest_path)
    if manifest.get("status") != "PASS_WRITE_FREE_CHUNK_GRAPH_PLAN":
        raise StagingLoadBlocked("chunk_graph_plan_not_passed")
    if manifest.get("eligible_for_write_free_dry_run") is not True:
        raise StagingLoadBlocked("chunk_graph_plan_not_dry_run_eligible")
    if manifest.get("controls", {}).get("automatic_promotions") != 0:
        raise StagingLoadBlocked("chunk_automatic_promotions_not_zero")
    if manifest.get("controls", {}).get("neo4j_writes") != 0:
        raise StagingLoadBlocked("chunk_plan_write_count_not_zero")
    if manifest.get("controls", {}).get(
        "pending_context_queue_included"
    ) != 0:
        raise StagingLoadBlocked("pending_context_queue_in_plan")

    for name, expected in manifest.get("artifacts", {}).items():
        path = plan_dir / name
        if not path.is_file():
            raise StagingLoadBlocked(f"{name}:missing")
        if sha256_file(path) != expected.get("sha256"):
            raise StagingLoadBlocked(f"{name}:sha256_mismatch")
        if path.stat().st_size != expected.get("bytes"):
            raise StagingLoadBlocked(f"{name}:byte_count_mismatch")
        if len(_read_jsonl(path)) != expected.get("record_count"):
            raise StagingLoadBlocked(f"{name}:record_count_mismatch")

    nodes = _read_jsonl(plan_dir / "chunk_nodes.jsonl")
    edges = _read_jsonl(plan_dir / "chunk_dictionary_edges.jsonl")
    node_keys = {row.get("node_key") for row in nodes}
    if len(node_keys) != len(nodes) or None in node_keys:
        raise StagingLoadBlocked("duplicate_or_missing_chunk_node_key")
    edge_ids = {row.get("edge_id") for row in edges}
    if len(edge_ids) != len(edges) or None in edge_ids:
        raise StagingLoadBlocked("duplicate_or_missing_chunk_edge_id")
    for row in nodes:
        if row.get("labels") != ["Chunk"]:
            raise StagingLoadBlocked("chunk_node_label_invalid")
        if not LABEL_PATTERN.fullmatch("Chunk"):
            raise StagingLoadBlocked("chunk_label_invalid")
    for row in edges:
        relation_type = str(row.get("relation_type", ""))
        if (
            relation_type not in ALLOWED_CHUNK_RELATIONS
            or not RELATION_PATTERN.fullmatch(relation_type)
        ):
            raise StagingLoadBlocked("chunk_relation_type_invalid")
        if row.get("source_node_key") not in node_keys:
            raise StagingLoadBlocked("chunk_edge_source_missing")
        if not str(row.get("target_node_key", "")).startswith(
            "GlossaryEntry:"
        ):
            raise StagingLoadBlocked(
                "chunk_edge_target_not_dictionary_card"
            )
        properties = row.get("properties", {})
        if properties.get("automatic_promotion") is not False:
            raise StagingLoadBlocked("chunk_edge_automatic_promotion")
        if (
            relation_type == "LINKED_TO"
            and properties.get("review_status") != "VERIFIED"
        ):
            raise StagingLoadBlocked("linked_to_not_verified")
        if (
            relation_type == "HAS_CANDIDATE"
            and properties.get("review_status")
            != "DETERMINISTIC_CANDIDATE"
        ):
            raise StagingLoadBlocked("candidate_status_invalid")

    normalized_manifest = {
        **manifest,
        "source_release_id": manifest["dictionary_release_id"],
    }
    return {
        "plan_dir": plan_dir,
        "manifest_path": manifest_path,
        "manifest": normalized_manifest,
        "nodes": nodes,
        "edges": edges,
        "candidates": [],
    }


def validate_chunk_execution_gates(
    plan: dict[str, Any],
    dictionary_load_evidence: dict[str, Any],
    target_audit: dict[str, Any],
) -> dict[str, Any]:
    """Require dictionary-first ordering and an explicit staging target."""
    blockers: list[str] = []
    if dictionary_load_evidence.get("status") != (
        "PASS_CANONICAL_DICTIONARY_LOADED_TO_STAGING"
    ):
        blockers.append("DICTIONARY_STAGING_LOAD_REQUIRED")
    if dictionary_load_evidence.get("source_release_id") != plan[
        "manifest"
    ].get("dictionary_release_id"):
        blockers.append("DICTIONARY_RELEASE_ID_MISMATCH")
    if dictionary_load_evidence.get(
        "post_load_validation",
        {},
    ).get("status") != "PASS_POST_LOAD_VALIDATION":
        blockers.append("DICTIONARY_POST_LOAD_VALIDATION_REQUIRED")
    if target_audit.get("status") != (
        "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
    ):
        blockers.append("STATIC_NONPRODUCTION_TARGET_AUDIT_REQUIRED")
    if target_audit.get(
        "eligible_for_readonly_runtime_verification"
    ) is not True:
        blockers.append("READONLY_TARGET_VERIFICATION_NOT_ELIGIBLE")
    return {
        "status": (
            "PASS_CHUNK_EXECUTION_GATES"
            if not blockers
            else "BLOCKED_CHUNK_EXECUTION_GATES"
        ),
        "blockers": blockers,
        "eligible_for_staging_execution": not blockers,
        "eligible_for_production_execution": False,
    }


def inspect_chunk_execution_readiness(
    plan_dir: Path,
    dictionary_load_evidence_path: Path,
    env_path: Path,
) -> dict[str, Any]:
    """Inspect local gates without importing the Neo4j driver."""
    plan = load_chunk_plan(plan_dir)
    dictionary_evidence = _read_json(
        Path(dictionary_load_evidence_path).resolve()
    )
    target_audit = audit_target_values(
        _read_env(Path(env_path).resolve())
    )
    gates = validate_chunk_execution_gates(
        plan,
        dictionary_evidence,
        target_audit,
    )
    return {
        **gates,
        "source_plan_id": plan["manifest"]["plan_id"],
        "dictionary_release_id": plan["manifest"][
            "dictionary_release_id"
        ],
        "neo4j_driver_imported": False,
        "neo4j_connections": 0,
        "neo4j_reads": 0,
        "neo4j_writes": 0,
    }


def execute_chunk_staging_load(
    plan_dir: Path,
    dictionary_load_evidence_path: Path,
    env_path: Path,
    evidence_dir: Path,
    batch_size: int = 250,
) -> dict[str, Any]:
    """Load accepted chunks only after their dictionary is present."""
    if batch_size < 1:
        raise StagingLoadBlocked("batch_size_must_be_positive")
    plan = load_chunk_plan(plan_dir)
    dictionary_evidence = _read_json(
        Path(dictionary_load_evidence_path).resolve()
    )
    env_values = _read_env(Path(env_path).resolve())
    target_audit = audit_target_values(env_values)
    gates = validate_chunk_execution_gates(
        plan,
        dictionary_evidence,
        target_audit,
    )
    if not gates["eligible_for_staging_execution"]:
        raise StagingLoadBlocked(";".join(gates["blockers"]))

    batch_id = (
        "CHUNKBATCH-"
        + hashlib.sha256(
            (
                f"{plan['manifest']['dictionary_release_id']}|"
                f"{plan['manifest']['plan_id']}"
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )
    evidence_dir = Path(evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = evidence_dir / f"{batch_id}.preload_snapshot.json"
    target_keys = sorted(
        {row["target_node_key"] for row in plan["edges"]}
    )

    from neo4j import GraphDatabase

    uri = env_values["NEO4J_URI"]
    user = env_values.get("NEO4J_USER") or env_values.get(
        "NEO4J_USERNAME"
    )
    password = env_values["NEO4J_PASSWORD"]
    database = env_values.get("NEO4J_DATABASE") or None
    driver = GraphDatabase.driver(uri, auth=(user, password))
    session_kwargs = {"database": database} if database else {}
    try:
        with driver.session(**session_kwargs) as session:
            endpoint_row = session.run(
                "MATCH (n:GlossaryEntry) "
                "WHERE n.node_key IN $target_keys "
                "AND n.dictionary_release_id = $release_id "
                "RETURN count(n) AS count",
                target_keys=target_keys,
                release_id=plan["manifest"]["dictionary_release_id"],
            ).single()
            endpoint_count = int(endpoint_row["count"])
            if endpoint_count != len(target_keys):
                raise StagingLoadBlocked(
                    "RUNTIME_DICTIONARY_ENDPOINTS_MISSING"
                )
            snapshot = _snapshot(session, plan, batch_id)
            snapshot["target_runtime_verification"] = {
                "status": (
                    "PASS_DICTIONARY_PREDECESSOR_AND_ENDPOINTS"
                ),
                "dictionary_release_id": plan["manifest"][
                    "dictionary_release_id"
                ],
                "expected_dictionary_endpoints": len(target_keys),
                "actual_dictionary_endpoints": endpoint_count,
                "secrets_emitted": False,
            }
            snapshot_sha = _write_snapshot(snapshot, snapshot_path)
            for _, query in [*CONSTRAINTS, CHUNK_CONSTRAINT]:
                session.run(query).consume()
            loaded_nodes = _load_nodes(
                session,
                plan,
                snapshot,
                batch_id,
                batch_size,
            )
            loaded_edges = _load_edges(
                session,
                plan,
                snapshot,
                batch_id,
                batch_size,
            )
            post_load = _post_load_validation(session, plan)
            if post_load["errors"]:
                raise StagingLoadBlocked(
                    ";".join(post_load["errors"])
                )
    finally:
        driver.close()

    evidence = {
        "schema_version": "0.1",
        "status": "PASS_CANONICAL_CHUNK_CONTEXT_LOADED_TO_STAGING",
        "ingestion_batch_id": batch_id,
        "dictionary_release_id": plan["manifest"][
            "dictionary_release_id"
        ],
        "source_plan_id": plan["manifest"]["plan_id"],
        "preload_snapshot_path": str(snapshot_path),
        "preload_snapshot_sha256": snapshot_sha,
        "chunk_nodes_loaded_or_updated": loaded_nodes,
        "chunk_relationships_loaded_or_updated": loaded_edges,
        "post_load_validation": post_load,
        "pending_context_queue_loaded": 0,
        "automatic_promotions": 0,
        "target_classification": (
            "EXPLICIT_NONPRODUCTION_CONFIGURATION"
        ),
        "secrets_emitted": False,
        "eligible_for_production_execution": False,
    }
    evidence_path = evidence_dir / f"{batch_id}.load_evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return evidence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-dir", required=True, type=Path)
    parser.add_argument(
        "--dictionary-load-evidence",
        required=True,
        type=Path,
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("out/unified_program/chunk_staging_evidence"),
    )
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--execute-staging", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.execute_staging:
            report = execute_chunk_staging_load(
                args.plan_dir,
                args.dictionary_load_evidence,
                args.env_file,
                args.evidence_dir,
                args.batch_size,
            )
        else:
            report = inspect_chunk_execution_readiness(
                args.plan_dir,
                args.dictionary_load_evidence,
                args.env_file,
            )
    except StagingLoadBlocked as error:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": str(error),
                    "neo4j_connections": 0,
                    "neo4j_writes": 0,
                    "eligible_for_production_execution": False,
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
