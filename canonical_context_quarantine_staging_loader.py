# -*- coding: utf-8 -*-
"""Guarded staging loader for quarantined chunk-context evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

from dictionary_release_acceptance import sha256_file
from neo4j_target_static_audit import _read_env, audit_target_values


ALLOWED_LABELS = {
    "ChunkEvidenceExcerpt",
    "QuarantinedEvidence",
    "ClinicalContextRelationCandidate",
    "QuarantinedCandidate",
}
ALLOWED_RELATIONS = {
    "SUPPORTED_BY_EXCERPT",
    "CANDIDATE_SOURCE_ENDPOINT",
    "CANDIDATE_TARGET_ENDPOINT",
}
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


class ContextQuarantineLoadBlocked(RuntimeError):
    """Raised when a quarantine staging gate or invariant fails."""


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
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ContextQuarantineLoadBlocked(
                f"{path.name}:{line_number}:not_object"
            )
        rows.append(row)
    return rows


def _safe_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(
            item is None or isinstance(item, (str, int, float, bool))
            for item in value
        )
    return False


def _chunks(
    rows: list[dict[str, Any]],
    size: int,
) -> Iterable[list[dict[str, Any]]]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def load_plan(plan_dir: Path) -> dict[str, Any]:
    plan_dir = Path(plan_dir).resolve()
    manifest_path = (
        plan_dir / "context_quarantine_graph_plan_manifest.json"
    )
    if not manifest_path.is_file():
        raise ContextQuarantineLoadBlocked("plan_manifest_missing")
    manifest = _read_json(manifest_path)
    if manifest.get("status") != (
        "PASS_WRITE_FREE_CONTEXT_QUARANTINE_PLAN"
    ):
        raise ContextQuarantineLoadBlocked("plan_status_invalid")
    controls = manifest.get("controls", {})
    if (
        controls.get("canonical_semantic_edges") != 0
        or controls.get("automatic_promotions") != 0
        or controls.get("neo4j_writes") != 0
    ):
        raise ContextQuarantineLoadBlocked(
            "plan_safety_controls_failed"
        )
    for name, expected in manifest.get("artifacts", {}).items():
        path = plan_dir / name
        if (
            not path.is_file()
            or sha256_file(path) != expected.get("sha256")
            or path.stat().st_size != expected.get("bytes")
            or len(_read_jsonl(path)) != expected.get("record_count")
        ):
            raise ContextQuarantineLoadBlocked(
                f"{name}:integrity_failure"
            )
    nodes = _read_jsonl(plan_dir / "context_quarantine_nodes.jsonl")
    edges = _read_jsonl(plan_dir / "context_quarantine_edges.jsonl")
    node_keys = {str(row.get("node_key", "")) for row in nodes}
    edge_ids = {str(row.get("edge_id", "")) for row in edges}
    if "" in node_keys or len(node_keys) != len(nodes):
        raise ContextQuarantineLoadBlocked(
            "duplicate_or_missing_node_key"
        )
    if "" in edge_ids or len(edge_ids) != len(edges):
        raise ContextQuarantineLoadBlocked(
            "duplicate_or_missing_edge_id"
        )
    for row in nodes:
        labels = row.get("labels", [])
        if (
            not isinstance(labels, list)
            or not labels
            or not set(labels).issubset(ALLOWED_LABELS)
            or any(
                not IDENTIFIER_PATTERN.fullmatch(str(label))
                for label in labels
            )
            or any(
                not _safe_value(value)
                for value in row.get("properties", {}).values()
            )
        ):
            raise ContextQuarantineLoadBlocked(
                f"{row.get('node_key')}:invalid_node"
            )
    for row in edges:
        relation_type = str(row.get("relation_type", ""))
        target_key = str(row.get("target_node_key", ""))
        if (
            relation_type not in ALLOWED_RELATIONS
            or not IDENTIFIER_PATTERN.fullmatch(relation_type)
            or row.get("source_node_key") not in node_keys
            or (
                target_key not in node_keys
                and not target_key.startswith("GlossaryEntry:")
            )
            or any(
                not _safe_value(value)
                for value in row.get("properties", {}).values()
            )
        ):
            raise ContextQuarantineLoadBlocked(
                f"{row.get('edge_id')}:invalid_edge"
            )
    return {
        "manifest": manifest,
        "manifest_path": manifest_path,
        "nodes": nodes,
        "edges": edges,
    }


def validate_gates(
    plan: dict[str, Any],
    dictionary_load_evidence: dict[str, Any],
    target_audit: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    manifest = plan["manifest"]
    if dictionary_load_evidence.get("status") != (
        "PASS_CANONICAL_DICTIONARY_LOADED_TO_STAGING"
    ):
        blockers.append("DICTIONARY_STAGING_LOAD_REQUIRED")
    if dictionary_load_evidence.get("source_release_id") != (
        manifest.get("dictionary_release_id")
    ):
        blockers.append("DICTIONARY_RELEASE_MISMATCH")
    if dictionary_load_evidence.get(
        "post_load_validation", {}
    ).get("status") != "PASS_POST_LOAD_VALIDATION":
        blockers.append("DICTIONARY_POSTLOAD_VALIDATION_REQUIRED")
    if target_audit.get("status") != (
        "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
    ):
        blockers.append("NONPRODUCTION_TARGET_REQUIRED")
    return {
        "status": (
            "PASS_CONTEXT_QUARANTINE_EXECUTION_GATES"
            if not blockers
            else "BLOCKED_CONTEXT_QUARANTINE_EXECUTION_GATES"
        ),
        "blockers": blockers,
        "eligible_for_staging_quarantine_execution": not blockers,
        "eligible_for_canonical_relation_load": False,
        "eligible_for_production_execution": False,
    }


def inspect_readiness(
    plan_dir: Path,
    dictionary_load_evidence_path: Path,
    env_path: Path,
) -> dict[str, Any]:
    plan = load_plan(plan_dir)
    dictionary_evidence = _read_json(
        Path(dictionary_load_evidence_path).resolve()
    )
    target_audit = audit_target_values(
        _read_env(Path(env_path).resolve())
    )
    gates = validate_gates(plan, dictionary_evidence, target_audit)
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


def _result_data(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "data"):
        return list(result.data())
    return [dict(row) for row in result]


def execute_staging_quarantine_load(
    plan_dir: Path,
    dictionary_load_evidence_path: Path,
    env_path: Path,
    evidence_dir: Path,
    batch_size: int = 250,
    driver_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    if batch_size < 1:
        raise ContextQuarantineLoadBlocked(
            "batch_size_must_be_positive"
        )
    plan = load_plan(plan_dir)
    dictionary_evidence = _read_json(
        Path(dictionary_load_evidence_path).resolve()
    )
    env_values = _read_env(Path(env_path).resolve())
    target_audit = audit_target_values(env_values)
    gates = validate_gates(plan, dictionary_evidence, target_audit)
    if not gates["eligible_for_staging_quarantine_execution"]:
        raise ContextQuarantineLoadBlocked(
            ";".join(gates["blockers"])
        )
    if driver_factory is None:
        from neo4j import GraphDatabase

        driver_factory = GraphDatabase.driver

    batch_id = (
        "CONTEXTBATCH-"
        + hashlib.sha256(
            (
                f"{plan['manifest']['plan_id']}|"
                f"{dictionary_evidence['ingestion_batch_id']}"
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )
    node_keys = [row["node_key"] for row in plan["nodes"]]
    edge_ids = [row["edge_id"] for row in plan["edges"]]
    card_node_keys = sorted(
        {
            str(row["target_node_key"])
            for row in plan["edges"]
            if str(row["target_node_key"]).startswith(
                "GlossaryEntry:"
            )
        }
    )
    driver = driver_factory(
        env_values["NEO4J_URI"],
        auth=(
            env_values.get("NEO4J_USER")
            or env_values.get("NEO4J_USERNAME"),
            env_values["NEO4J_PASSWORD"],
        ),
    )
    database = env_values.get("NEO4J_DATABASE") or None
    session_kwargs = {"database": database} if database else {}
    evidence_dir = Path(evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = (
        evidence_dir / f"{batch_id}.preload_snapshot.json"
    )
    try:
        if hasattr(driver, "verify_connectivity"):
            driver.verify_connectivity()
        with driver.session(**session_kwargs) as session:
            database_row = session.run(
                "CALL db.info() YIELD name "
                "RETURN name AS database_name"
            ).single()
            existing_nodes = _result_data(
                session.run(
                    "MATCH (n) WHERE n.node_key IN $node_keys "
                    "RETURN n.node_key AS node_key",
                    node_keys=node_keys,
                )
            )
            existing_edges = _result_data(
                session.run(
                    "MATCH ()-[r]->() WHERE r.edge_id IN $edge_ids "
                    "RETURN r.edge_id AS edge_id",
                    edge_ids=edge_ids,
                )
            )
            card_rows = _result_data(
                session.run(
                    "MATCH (n:GlossaryEntry) "
                    "WHERE n.node_key IN $node_keys "
                    "RETURN n.node_key AS node_key",
                    node_keys=card_node_keys,
                )
            )
            found_cards = {row["node_key"] for row in card_rows}
            if existing_nodes or existing_edges:
                raise ContextQuarantineLoadBlocked(
                    "QUARANTINE_PLAN_KEYS_ALREADY_EXIST"
                )
            if found_cards != set(card_node_keys):
                raise ContextQuarantineLoadBlocked(
                    "DICTIONARY_ENDPOINTS_MISSING_AT_RUNTIME"
                )
            snapshot = {
                "schema_version": "0.1",
                "status": "PRELOAD_CONTEXT_QUARANTINE_SNAPSHOT_COMPLETE",
                "ingestion_batch_id": batch_id,
                "source_plan_id": plan["manifest"]["plan_id"],
                "dictionary_release_id": plan["manifest"][
                    "dictionary_release_id"
                ],
                "runtime_database": str(
                    database_row["database_name"]
                ),
                "existing_nodes": [],
                "existing_relationships": [],
                "created_node_keys_if_load_succeeds": sorted(
                    node_keys
                ),
                "created_edge_ids_if_load_succeeds": sorted(edge_ids),
                "verified_dictionary_endpoint_count": len(found_cards),
                "neo4j_reads_performed": 4,
                "neo4j_writes_performed": 0,
            }
            snapshot_path.write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2)
                + "\n",
                encoding="utf-8",
            )
            snapshot_sha = sha256_file(snapshot_path)

            session.run(
                "CREATE CONSTRAINT context_quarantine_node_key_unique "
                "IF NOT EXISTS FOR (n:ContextQuarantineEntity) "
                "REQUIRE n.node_key IS UNIQUE"
            ).consume()

            grouped_nodes: dict[
                tuple[str, ...],
                list[dict[str, Any]],
            ] = defaultdict(list)
            for row in plan["nodes"]:
                grouped_nodes[tuple(sorted(row["labels"]))].append(
                    row
                )
            nodes_loaded = 0
            for labels, rows in sorted(grouped_nodes.items()):
                label_clause = ":".join(
                    ["ContextQuarantineEntity", *labels]
                )
                query = (
                    "UNWIND $rows AS row "
                    f"CREATE (n:{label_clause} "
                    "{node_key: row.node_key}) "
                    "SET n += row.properties, "
                    "n.last_ingestion_batch_id = $batch_id, "
                    "n.created_by_ingestion_batch_id = $batch_id"
                )
                for batch in _chunks(rows, batch_size):
                    session.run(
                        query,
                        rows=batch,
                        batch_id=batch_id,
                    ).consume()
                    nodes_loaded += len(batch)

            grouped_edges: dict[
                tuple[str, str],
                list[dict[str, Any]],
            ] = defaultdict(list)
            for row in plan["edges"]:
                target_class = (
                    "GlossaryEntry"
                    if str(row["target_node_key"]).startswith(
                        "GlossaryEntry:"
                    )
                    else "ContextQuarantineEntity"
                )
                grouped_edges[
                    (row["relation_type"], target_class)
                ].append(row)
            edges_loaded = 0
            for (
                relation_type,
                target_class,
            ), rows in sorted(grouped_edges.items()):
                query = (
                    "UNWIND $rows AS row "
                    "MATCH (s:ContextQuarantineEntity "
                    "{node_key: row.source_node_key}) "
                    f"MATCH (t:{target_class} "
                    "{node_key: row.target_node_key}) "
                    f"CREATE (s)-[r:{relation_type} "
                    "{edge_id: row.edge_id}]->(t) "
                    "SET r += row.properties, "
                    "r.last_ingestion_batch_id = $batch_id, "
                    "r.created_by_ingestion_batch_id = $batch_id"
                )
                for batch in _chunks(rows, batch_size):
                    session.run(
                        query,
                        rows=batch,
                        batch_id=batch_id,
                    ).consume()
                    edges_loaded += len(batch)

            node_count = int(
                session.run(
                    "MATCH (n:ContextQuarantineEntity "
                    "{created_by_ingestion_batch_id: $batch_id}) "
                    "RETURN count(n) AS count",
                    batch_id=batch_id,
                ).single()["count"]
            )
            edge_count = int(
                session.run(
                    "MATCH ()-[r]->() "
                    "WHERE r.created_by_ingestion_batch_id = $batch_id "
                    "RETURN count(r) AS count",
                    batch_id=batch_id,
                ).single()["count"]
            )
    finally:
        driver.close()

    errors: list[str] = []
    if node_count != len(plan["nodes"]):
        errors.append("POST_LOAD_NODE_COUNT_MISMATCH")
    if edge_count != len(plan["edges"]):
        errors.append("POST_LOAD_EDGE_COUNT_MISMATCH")
    if errors:
        raise ContextQuarantineLoadBlocked(";".join(errors))
    evidence = {
        "schema_version": "0.1",
        "status": "PASS_CONTEXT_QUARANTINE_LOADED_TO_STAGING",
        "ingestion_batch_id": batch_id,
        "source_plan_id": plan["manifest"]["plan_id"],
        "dictionary_release_id": plan["manifest"][
            "dictionary_release_id"
        ],
        "dictionary_ingestion_batch_id": dictionary_evidence[
            "ingestion_batch_id"
        ],
        "preload_snapshot_path": str(snapshot_path),
        "preload_snapshot_sha256": snapshot_sha,
        "nodes_loaded": nodes_loaded,
        "relationships_loaded": edges_loaded,
        "post_load_validation": {
            "status": "PASS_CONTEXT_QUARANTINE_POST_LOAD_VALIDATION",
            "expected_nodes": len(plan["nodes"]),
            "actual_nodes": node_count,
            "expected_edges": len(plan["edges"]),
            "actual_edges": edge_count,
            "errors": [],
        },
        "canonical_semantic_edges_loaded": 0,
        "automatic_promotions": 0,
        "target_classification": (
            "EXPLICIT_NONPRODUCTION_CONFIGURATION"
        ),
        "eligible_for_canonical_relation_load": False,
        "eligible_for_production_execution": False,
    }
    evidence_path = evidence_dir / f"{batch_id}.load_evidence.json"
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return evidence


def rollback_staging_quarantine_load(
    snapshot_path: Path,
    env_path: Path,
    evidence_dir: Path,
    driver_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    snapshot_path = Path(snapshot_path).resolve()
    snapshot = _read_json(snapshot_path)
    if snapshot.get("status") != (
        "PRELOAD_CONTEXT_QUARANTINE_SNAPSHOT_COMPLETE"
    ):
        raise ContextQuarantineLoadBlocked("snapshot_status_invalid")
    if snapshot.get("existing_nodes") or snapshot.get(
        "existing_relationships"
    ):
        raise ContextQuarantineLoadBlocked(
            "NONEMPTY_SNAPSHOT_NOT_SUPPORTED"
        )
    env_values = _read_env(Path(env_path).resolve())
    target_audit = audit_target_values(env_values)
    if target_audit.get("status") != (
        "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
    ):
        raise ContextQuarantineLoadBlocked(
            "NONPRODUCTION_TARGET_REQUIRED"
        )
    if driver_factory is None:
        from neo4j import GraphDatabase

        driver_factory = GraphDatabase.driver
    driver = driver_factory(
        env_values["NEO4J_URI"],
        auth=(
            env_values.get("NEO4J_USER")
            or env_values.get("NEO4J_USERNAME"),
            env_values["NEO4J_PASSWORD"],
        ),
    )
    database = env_values.get("NEO4J_DATABASE") or None
    session_kwargs = {"database": database} if database else {}
    batch_id = snapshot["ingestion_batch_id"]
    try:
        with driver.session(**session_kwargs) as session:
            deleted_edges = int(
                session.run(
                    "MATCH ()-[r]->() "
                    "WHERE r.created_by_ingestion_batch_id = $batch_id "
                    "WITH r DELETE r RETURN count(*) AS count",
                    batch_id=batch_id,
                ).single()["count"]
            )
            deleted_nodes = int(
                session.run(
                    "MATCH (n:ContextQuarantineEntity "
                    "{created_by_ingestion_batch_id: $batch_id}) "
                    "WITH n DELETE n RETURN count(*) AS count",
                    batch_id=batch_id,
                ).single()["count"]
            )
            remaining = int(
                session.run(
                    "MATCH (n:ContextQuarantineEntity "
                    "{created_by_ingestion_batch_id: $batch_id}) "
                    "RETURN count(n) AS count",
                    batch_id=batch_id,
                ).single()["count"]
            )
    finally:
        driver.close()
    evidence = {
        "schema_version": "0.1",
        "status": (
            "PASS_CONTEXT_QUARANTINE_BATCH_ROLLBACK"
            if remaining == 0
            else "BLOCKED_CONTEXT_QUARANTINE_ROLLBACK"
        ),
        "ingestion_batch_id": batch_id,
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": sha256_file(snapshot_path),
        "relationships_deleted": deleted_edges,
        "nodes_deleted": deleted_nodes,
        "remaining_batch_nodes": remaining,
        "eligible_for_production_execution": False,
    }
    evidence_dir = Path(evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    path = evidence_dir / f"{batch_id}.rollback_evidence.json"
    path.write_text(
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
        default=Path(
            "out/unified_program/context_quarantine_staging_evidence"
        ),
    )
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--execute-staging", action="store_true")
    parser.add_argument("--rollback-snapshot", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        if args.execute_staging and args.rollback_snapshot:
            raise ContextQuarantineLoadBlocked(
                "execute_and_rollback_are_mutually_exclusive"
            )
        if args.rollback_snapshot:
            report = rollback_staging_quarantine_load(
                args.rollback_snapshot,
                args.env_file,
                args.evidence_dir,
            )
        elif args.execute_staging:
            report = execute_staging_quarantine_load(
                args.plan_dir,
                args.dictionary_load_evidence,
                args.env_file,
                args.evidence_dir,
                args.batch_size,
            )
        else:
            report = inspect_readiness(
                args.plan_dir,
                args.dictionary_load_evidence,
                args.env_file,
            )
    except ContextQuarantineLoadBlocked as error:
        report = {
            "status": "BLOCKED_CONTEXT_QUARANTINE_LOAD",
            "error": str(error),
            "neo4j_connections": 0,
            "neo4j_writes": 0,
            "eligible_for_canonical_relation_load": False,
            "eligible_for_production_execution": False,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
