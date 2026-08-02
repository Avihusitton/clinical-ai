# -*- coding: utf-8 -*-
"""Guarded Neo4j staging loader for an accepted canonical graph plan."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Callable, Iterable

from dictionary_release_acceptance import (
    CANONICAL_MANIFEST_STATUSES,
    sha256_file,
)
from neo4j_target_static_audit import _read_env, audit_target_values


LABEL_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
RELATION_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")
KNOWN_PLAN_LABELS = {
    "DictionaryEntity",
    "GlossaryEntry",
    "Concept",
    "Exercise",
    "DictionaryRedirect",
    "SourceDocument",
    "Chunk",
}
CONSTRAINTS = [
    (
        "dictionary_entity_node_key_unique",
        "CREATE CONSTRAINT dictionary_entity_node_key_unique "
        "IF NOT EXISTS FOR (n:DictionaryEntity) "
        "REQUIRE n.node_key IS UNIQUE",
    ),
    (
        "glossaryentry_card_id_unique",
        "CREATE CONSTRAINT glossaryentry_card_id_unique "
        "IF NOT EXISTS FOR (n:GlossaryEntry) "
        "REQUIRE n.card_id IS UNIQUE",
    ),
    (
        "source_document_id_unique",
        "CREATE CONSTRAINT source_document_id_unique "
        "IF NOT EXISTS FOR (n:SourceDocument) "
        "REQUIRE n.source_document_id IS UNIQUE",
    ),
]


class StagingLoadBlocked(RuntimeError):
    """Raised when a staging execution gate or invariant fails."""


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
            raise StagingLoadBlocked(
                f"{path.name}:{line_number}:invalid_json"
            ) from error
        if not isinstance(row, dict):
            raise StagingLoadBlocked(
                f"{path.name}:{line_number}:record_not_object"
            )
        rows.append(row)
    return rows


def _find_one(directory: Path, pattern: str) -> Path:
    paths = sorted(directory.glob(pattern))
    if len(paths) != 1:
        raise StagingLoadBlocked(
            f"{pattern}:artifact_count:{len(paths)}"
        )
    return paths[0]


def _neo4j_safe_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, list):
        return all(
            item is None or isinstance(item, (str, int, float, bool))
            for item in value
        )
    return False


def _validate_properties(
    properties: dict[str, Any],
    identity: str,
) -> None:
    invalid = [
        key
        for key, value in properties.items()
        if not _neo4j_safe_value(value)
    ]
    if invalid:
        raise StagingLoadBlocked(
            f"{identity}:neo4j_unsafe_properties:{','.join(sorted(invalid))}"
        )


def load_plan(plan_dir: Path) -> dict[str, Any]:
    """Read and independently verify a graph-plan package."""
    plan_dir = Path(plan_dir).resolve()
    manifest_path = _find_one(
        plan_dir,
        "dictionary_graph_plan_manifest*.json",
    )
    manifest = _read_json(manifest_path)
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

    nodes_path = _find_one(plan_dir, "dictionary_nodes*.jsonl")
    edges_path = _find_one(plan_dir, "dictionary_edges*.jsonl")
    candidates_path = _find_one(
        plan_dir,
        "dictionary_relation_candidates*.jsonl",
    )
    nodes = _read_jsonl(nodes_path)
    edges = _read_jsonl(edges_path)
    candidates = _read_jsonl(candidates_path)
    node_keys = {row.get("node_key") for row in nodes}
    if len(node_keys) != len(nodes) or None in node_keys:
        raise StagingLoadBlocked("duplicate_or_missing_node_key")
    edge_ids = {row.get("edge_id") for row in edges}
    if len(edge_ids) != len(edges) or None in edge_ids:
        raise StagingLoadBlocked("duplicate_or_missing_edge_id")

    for row in nodes:
        labels = row.get("labels", [])
        if (
            not isinstance(labels, list)
            or not labels
            or any(
                not LABEL_PATTERN.fullmatch(str(label))
                for label in labels
            )
        ):
            raise StagingLoadBlocked(
                f"{row.get('node_key')}:invalid_labels"
            )
        if not set(labels).issubset(KNOWN_PLAN_LABELS):
            raise StagingLoadBlocked(
                f"{row.get('node_key')}:unknown_labels"
            )
        _validate_properties(
            row.get("properties", {}),
            str(row["node_key"]),
        )
    for row in edges:
        edge_id = str(row.get("edge_id", ""))
        if (
            row.get("source_node_key") not in node_keys
            or row.get("target_node_key") not in node_keys
        ):
            raise StagingLoadBlocked(f"{edge_id}:missing_endpoint")
        if not RELATION_PATTERN.fullmatch(
            str(row.get("relation_type", ""))
        ):
            raise StagingLoadBlocked(f"{edge_id}:invalid_relation_type")
        _validate_properties(row.get("properties", {}), edge_id)
        if row.get("properties", {}).get("review_status") == (
            "PENDING_DICTIONARY_REVIEW"
        ):
            raise StagingLoadBlocked(f"{edge_id}:candidate_in_load_plan")

    return {
        "plan_dir": plan_dir,
        "manifest_path": manifest_path,
        "manifest": manifest,
        "nodes": nodes,
        "edges": edges,
        "candidates": candidates,
    }


def validate_execution_gates(
    plan: dict[str, Any],
    preflight_summary: dict[str, Any],
    target_audit: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless every canonical staging gate is satisfied."""
    blockers: list[str] = []
    manifest = plan["manifest"]
    if manifest.get("preview") is not False:
        blockers.append("PREVIEW_PLAN_FORBIDDEN")
    if manifest.get("source_manifest_status") not in (
        CANONICAL_MANIFEST_STATUSES
    ):
        blockers.append("CANONICAL_MANIFEST_STATUS_REQUIRED")
    if preflight_summary.get("status") != (
        "PASS_CANONICAL_READY_FOR_STAGING_TARGET_PREFLIGHT"
    ):
        blockers.append("CANONICAL_UNIFIED_PREFLIGHT_REQUIRED")
    if preflight_summary.get(
        "eligible_for_staging_target_verification"
    ) is not True:
        blockers.append("STAGING_TARGET_PREFLIGHT_NOT_ELIGIBLE")
    if preflight_summary.get("neo4j_writes") != 0:
        blockers.append("PREFLIGHT_WRITE_COUNT_NOT_ZERO")
    if target_audit.get("status") != (
        "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
    ):
        blockers.append("STATIC_NONPRODUCTION_TARGET_AUDIT_REQUIRED")
    if target_audit.get(
        "eligible_for_readonly_runtime_verification"
    ) is not True:
        blockers.append("READONLY_TARGET_VERIFICATION_NOT_ELIGIBLE")
    if plan["candidates"] and manifest.get("controls", {}).get(
        "candidate_edges_in_load_plan"
    ) != 0:
        blockers.append("CANDIDATE_EDGE_ISOLATION_FAILED")
    return {
        "status": (
            "PASS_EXECUTION_GATES"
            if not blockers
            else "BLOCKED_EXECUTION_GATES"
        ),
        "blockers": blockers,
        "eligible_for_staging_execution": not blockers,
        "eligible_for_production_execution": False,
    }


def _result_data(result: Any) -> list[dict[str, Any]]:
    if hasattr(result, "data"):
        return list(result.data())
    return [dict(row) for row in result]


def _snapshot(
    session: Any,
    plan: dict[str, Any],
    batch_id: str,
) -> dict[str, Any]:
    node_keys = [row["node_key"] for row in plan["nodes"]]
    edge_ids = [row["edge_id"] for row in plan["edges"]]
    existing_nodes = _result_data(
        session.run(
            "MATCH (n) WHERE n.node_key IN $node_keys "
            "RETURN n.node_key AS node_key, labels(n) AS labels, "
            "properties(n) AS properties ORDER BY node_key",
            node_keys=node_keys,
        )
    )
    existing_relationships = _result_data(
        session.run(
            "MATCH (s)-[r]->(t) WHERE r.edge_id IN $edge_ids "
            "RETURN r.edge_id AS edge_id, type(r) AS relation_type, "
            "s.node_key AS source_node_key, "
            "t.node_key AS target_node_key, "
            "properties(r) AS properties ORDER BY edge_id",
            edge_ids=edge_ids,
        )
    )
    existing_node_keys = {
        row["node_key"] for row in existing_nodes
    }
    existing_edge_ids = {
        row["edge_id"] for row in existing_relationships
    }
    return {
        "schema_version": "0.1",
        "status": "PRELOAD_SNAPSHOT_COMPLETE",
        "ingestion_batch_id": batch_id,
        "source_plan_id": plan["manifest"]["plan_id"],
        "source_release_id": plan["manifest"]["source_release_id"],
        "existing_nodes": existing_nodes,
        "existing_relationships": existing_relationships,
        "created_node_keys_if_load_succeeds": sorted(
            set(node_keys) - existing_node_keys
        ),
        "created_edge_ids_if_load_succeeds": sorted(
            set(edge_ids) - existing_edge_ids
        ),
        "neo4j_reads_performed": 2,
        "neo4j_writes_performed": 0,
    }


def _write_snapshot(snapshot: dict[str, Any], path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            snapshot,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
        + "\n",
        encoding="utf-8",
    )
    return sha256_file(path)


def _chunks(rows: list[dict[str, Any]], size: int) -> Iterable[list]:
    for start in range(0, len(rows), size):
        yield rows[start : start + size]


def _load_nodes(
    session: Any,
    plan: dict[str, Any],
    snapshot: dict[str, Any],
    batch_id: str,
    batch_size: int,
) -> int:
    existing = {
        row["node_key"]: row.get("properties", {})
        for row in snapshot["existing_nodes"]
    }
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in plan["nodes"]:
        grouped[tuple(sorted(row["labels"]))].append(
            {
                "node_key": row["node_key"],
                "properties": row["properties"],
                "created_by_ingestion_batch_id": (
                    batch_id
                    if row["node_key"] not in existing
                    else existing[row["node_key"]].get(
                        "created_by_ingestion_batch_id"
                    )
                ),
            }
        )
    remove_clause = " ".join(
        f"REMOVE n:{label}"
        for label in sorted(KNOWN_PLAN_LABELS - {"DictionaryEntity"})
    )
    loaded = 0
    for labels, rows in sorted(grouped.items()):
        set_labels = ":".join(["DictionaryEntity", *labels])
        query = (
            "UNWIND $rows AS row "
            "MERGE (n:DictionaryEntity {node_key: row.node_key}) "
            "SET n = row.properties, "
            "n.node_key = row.node_key, "
            "n.last_ingestion_batch_id = $batch_id, "
            "n.dictionary_release_id = $release_id, "
            "n.created_by_ingestion_batch_id = "
            "row.created_by_ingestion_batch_id "
            f"{remove_clause} "
            f"SET n:{set_labels}"
        )
        for batch in _chunks(rows, batch_size):
            session.run(
                query,
                rows=batch,
                batch_id=batch_id,
                release_id=plan["manifest"]["source_release_id"],
            ).consume()
            loaded += len(batch)
    return loaded


def _load_edges(
    session: Any,
    plan: dict[str, Any],
    snapshot: dict[str, Any],
    batch_id: str,
    batch_size: int,
) -> int:
    existing = {
        row["edge_id"]: row.get("properties", {})
        for row in snapshot["existing_relationships"]
    }
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in plan["edges"]:
        grouped[row["relation_type"]].append(
            {
                "edge_id": row["edge_id"],
                "source_node_key": row["source_node_key"],
                "target_node_key": row["target_node_key"],
                "properties": row["properties"],
                "created_by_ingestion_batch_id": (
                    batch_id
                    if row["edge_id"] not in existing
                    else existing[row["edge_id"]].get(
                        "created_by_ingestion_batch_id"
                    )
                ),
            }
        )
    loaded = 0
    for relation_type, rows in sorted(grouped.items()):
        if not RELATION_PATTERN.fullmatch(relation_type):
            raise StagingLoadBlocked("invalid_relation_type")
        query = (
            "UNWIND $rows AS row "
            "MATCH (s:DictionaryEntity {node_key: row.source_node_key}) "
            "MATCH (t:DictionaryEntity {node_key: row.target_node_key}) "
            f"MERGE (s)-[r:{relation_type} "
            "{edge_id: row.edge_id}]->(t) "
            "SET r = row.properties, "
            "r.edge_id = row.edge_id, "
            "r.last_ingestion_batch_id = $batch_id, "
            "r.created_by_ingestion_batch_id = "
            "row.created_by_ingestion_batch_id"
        )
        for batch in _chunks(rows, batch_size):
            session.run(
                query,
                rows=batch,
                batch_id=batch_id,
            ).consume()
            loaded += len(batch)
    return loaded


def _post_load_validation(
    session: Any,
    plan: dict[str, Any],
) -> dict[str, Any]:
    node_keys = [row["node_key"] for row in plan["nodes"]]
    edge_ids = [row["edge_id"] for row in plan["edges"]]
    node_row = session.run(
        "MATCH (n:DictionaryEntity) "
        "WHERE n.node_key IN $node_keys "
        "RETURN count(n) AS count",
        node_keys=node_keys,
    ).single()
    edge_row = session.run(
        "MATCH ()-[r]->() WHERE r.edge_id IN $edge_ids "
        "RETURN count(r) AS count",
        edge_ids=edge_ids,
    ).single()
    node_count = int(node_row["count"])
    edge_count = int(edge_row["count"])
    errors: list[str] = []
    if node_count != len(node_keys):
        errors.append("POST_LOAD_NODE_COUNT_MISMATCH")
    if edge_count != len(edge_ids):
        errors.append("POST_LOAD_EDGE_COUNT_MISMATCH")
    return {
        "status": (
            "PASS_POST_LOAD_VALIDATION"
            if not errors
            else "BLOCKED_POST_LOAD_VALIDATION"
        ),
        "expected_nodes": len(node_keys),
        "actual_nodes": node_count,
        "expected_edges": len(edge_ids),
        "actual_edges": edge_count,
        "errors": errors,
    }


def execute_staging_load(
    plan_dir: Path,
    preflight_summary_path: Path,
    env_path: Path,
    evidence_dir: Path,
    batch_size: int = 250,
) -> dict[str, Any]:
    """Execute a canonical load only after all non-production gates pass."""
    if batch_size < 1:
        raise StagingLoadBlocked("batch_size_must_be_positive")
    plan = load_plan(plan_dir)
    preflight = _read_json(Path(preflight_summary_path).resolve())
    env_values = _read_env(Path(env_path).resolve())
    target_audit = audit_target_values(env_values)
    gates = validate_execution_gates(plan, preflight, target_audit)
    if not gates["eligible_for_staging_execution"]:
        raise StagingLoadBlocked(";".join(gates["blockers"]))

    batch_id = (
        "DICTBATCH-"
        + hashlib.sha256(
            (
                f"{plan['manifest']['source_release_id']}|"
                f"{plan['manifest']['plan_id']}"
            ).encode("utf-8")
        ).hexdigest()[:20].upper()
    )
    evidence_dir = Path(evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    snapshot_path = evidence_dir / f"{batch_id}.preload_snapshot.json"

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
            server_row = session.run(
                "MATCH (n) RETURN count(n) AS node_count"
            ).single()
            snapshot = _snapshot(session, plan, batch_id)
            snapshot["target_runtime_verification"] = {
                "status": "PASS_READONLY_NONPRODUCTION_TARGET_REACHABLE",
                "database_configured": bool(database),
                "preload_total_node_count": int(
                    server_row["node_count"]
                ),
                "secrets_emitted": False,
            }
            snapshot_sha = _write_snapshot(snapshot, snapshot_path)

            for _, query in CONSTRAINTS:
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
        "status": "PASS_CANONICAL_DICTIONARY_LOADED_TO_STAGING",
        "ingestion_batch_id": batch_id,
        "source_release_id": plan["manifest"]["source_release_id"],
        "source_plan_id": plan["manifest"]["plan_id"],
        "preload_snapshot_path": str(snapshot_path),
        "preload_snapshot_sha256": snapshot_sha,
        "nodes_loaded_or_updated": loaded_nodes,
        "relationships_loaded_or_updated": loaded_edges,
        "post_load_validation": post_load,
        "candidate_edges_loaded": 0,
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


def _restore_nodes(
    session: Any,
    rows: list[dict[str, Any]],
    batch_size: int,
) -> int:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(
        list
    )
    for row in rows:
        labels = tuple(sorted(str(label) for label in row["labels"]))
        if any(not LABEL_PATTERN.fullmatch(label) for label in labels):
            raise StagingLoadBlocked("snapshot_contains_invalid_label")
        grouped[labels].append(row)
    remove_clause = " ".join(
        f"REMOVE n:{label}" for label in sorted(KNOWN_PLAN_LABELS)
    )
    restored = 0
    for labels, label_rows in sorted(grouped.items()):
        set_clause = (
            "SET n:" + ":".join(labels) if labels else ""
        )
        query = (
            "UNWIND $rows AS row "
            "MATCH (n {node_key: row.node_key}) "
            "SET n = row.properties "
            f"{remove_clause} "
            f"{set_clause}"
        )
        for batch in _chunks(label_rows, batch_size):
            session.run(query, rows=batch).consume()
            restored += len(batch)
    return restored


def _restore_relationships(
    session: Any,
    rows: list[dict[str, Any]],
    batch_size: int,
) -> int:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        relation_type = str(row["relation_type"])
        if not RELATION_PATTERN.fullmatch(relation_type):
            raise StagingLoadBlocked(
                "snapshot_contains_invalid_relation_type"
            )
        if not row.get("source_node_key") or not row.get(
            "target_node_key"
        ):
            raise StagingLoadBlocked(
                "snapshot_relationship_missing_node_key"
            )
        grouped[relation_type].append(row)
    restored = 0
    for relation_type, relation_rows in sorted(grouped.items()):
        query = (
            "UNWIND $rows AS row "
            "MATCH (s {node_key: row.source_node_key}) "
            "MATCH (t {node_key: row.target_node_key}) "
            f"CREATE (s)-[r:{relation_type}]->(t) "
            "SET r = row.properties"
        )
        for batch in _chunks(relation_rows, batch_size):
            session.run(query, rows=batch).consume()
            restored += len(batch)
    return restored


def rollback_staging_load(
    snapshot_path: Path,
    env_path: Path,
    evidence_dir: Path,
    batch_size: int = 250,
) -> dict[str, Any]:
    """Restore touched data from a preload snapshot by exact batch scope."""
    if batch_size < 1:
        raise StagingLoadBlocked("batch_size_must_be_positive")
    snapshot_path = Path(snapshot_path).resolve()
    snapshot = _read_json(snapshot_path)
    if snapshot.get("status") != "PRELOAD_SNAPSHOT_COMPLETE":
        raise StagingLoadBlocked("invalid_preload_snapshot_status")
    env_values = _read_env(Path(env_path).resolve())
    target_audit = audit_target_values(env_values)
    if target_audit.get("status") != (
        "PASS_STATIC_CONFIG_READY_FOR_READONLY_TARGET_VERIFICATION"
    ):
        raise StagingLoadBlocked("NONPRODUCTION_TARGET_REQUIRED")

    created_node_keys = snapshot.get(
        "created_node_keys_if_load_succeeds",
        [],
    )
    created_edge_ids = snapshot.get(
        "created_edge_ids_if_load_succeeds",
        [],
    )
    all_touched_edge_ids = sorted(
        set(created_edge_ids)
        | {
            row["edge_id"]
            for row in snapshot.get("existing_relationships", [])
        }
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
            session.run(
                "MATCH ()-[r]->() WHERE r.edge_id IN $edge_ids "
                "DELETE r",
                edge_ids=all_touched_edge_ids,
            ).consume()
            deleted_row = session.run(
                "MATCH (n) WHERE n.node_key IN $node_keys "
                "AND NOT (n)--() "
                "WITH n DELETE n RETURN count(*) AS deleted",
                node_keys=created_node_keys,
            ).single()
            restored_nodes = _restore_nodes(
                session,
                snapshot.get("existing_nodes", []),
                batch_size,
            )
            restored_relationships = _restore_relationships(
                session,
                snapshot.get("existing_relationships", []),
                batch_size,
            )
            remaining_row = session.run(
                "MATCH (n) WHERE n.node_key IN $node_keys "
                "RETURN count(n) AS count",
                node_keys=created_node_keys,
            ).single()
            created_edges_row = session.run(
                "MATCH ()-[r]->() "
                "WHERE r.edge_id IN $created_edge_ids "
                "RETURN count(r) AS count",
                created_edge_ids=created_edge_ids,
            ).single()
    finally:
        driver.close()

    remaining_created_nodes = int(remaining_row["count"])
    remaining_created_edges = int(created_edges_row["count"])
    errors: list[str] = []
    if remaining_created_nodes:
        errors.append("CREATED_NODES_REMAIN_AFTER_ROLLBACK")
    if remaining_created_edges:
        errors.append("CREATED_EDGES_REMAIN_AFTER_ROLLBACK")
    evidence = {
        "schema_version": "0.1",
        "status": (
            "PASS_BATCH_ROLLBACK"
            if not errors
            else "BLOCKED_BATCH_ROLLBACK_INCOMPLETE"
        ),
        "ingestion_batch_id": snapshot["ingestion_batch_id"],
        "snapshot_path": str(snapshot_path),
        "snapshot_sha256": sha256_file(snapshot_path),
        "created_nodes_deleted": int(deleted_row["deleted"]),
        "existing_nodes_restored": restored_nodes,
        "existing_relationships_restored": restored_relationships,
        "remaining_created_nodes": remaining_created_nodes,
        "remaining_created_edges": remaining_created_edges,
        "schema_constraints_retained": [
            name for name, _ in CONSTRAINTS
        ],
        "errors": errors,
        "target_classification": (
            "EXPLICIT_NONPRODUCTION_CONFIGURATION"
        ),
        "secrets_emitted": False,
        "eligible_for_production_execution": False,
    }
    evidence_dir = Path(evidence_dir).resolve()
    evidence_dir.mkdir(parents=True, exist_ok=True)
    evidence_path = (
        evidence_dir
        / f"{snapshot['ingestion_batch_id']}.rollback_evidence.json"
    )
    evidence_path.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return evidence


def inspect_execution_readiness(
    plan_dir: Path,
    preflight_summary_path: Path,
    env_path: Path,
) -> dict[str, Any]:
    """Inspect every local execution gate without importing Neo4j."""
    plan = load_plan(plan_dir)
    preflight = _read_json(Path(preflight_summary_path).resolve())
    target_audit = audit_target_values(
        _read_env(Path(env_path).resolve())
    )
    gates = validate_execution_gates(plan, preflight, target_audit)
    return {
        **gates,
        "source_plan_id": plan["manifest"]["plan_id"],
        "source_release_id": plan["manifest"]["source_release_id"],
        "target_static_audit_status": target_audit["status"],
        "neo4j_driver_imported": False,
        "neo4j_connections": 0,
        "neo4j_reads": 0,
        "neo4j_writes": 0,
    }


def verify_runtime_target(
    plan_dir: Path,
    preflight_summary_path: Path,
    env_path: Path,
    evidence_path: Path,
    driver_factory: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    """Verify the gated staging endpoint using read-only queries only."""
    plan = load_plan(plan_dir)
    preflight = _read_json(Path(preflight_summary_path).resolve())
    env_values = _read_env(Path(env_path).resolve())
    target_audit = audit_target_values(env_values)
    gates = validate_execution_gates(plan, preflight, target_audit)
    if not gates["eligible_for_staging_execution"]:
        raise StagingLoadBlocked(";".join(gates["blockers"]))

    if driver_factory is None:
        from neo4j import GraphDatabase

        driver_factory = GraphDatabase.driver

    uri = env_values["NEO4J_URI"]
    user = env_values.get("NEO4J_USER") or env_values.get(
        "NEO4J_USERNAME"
    )
    password = env_values["NEO4J_PASSWORD"]
    database = env_values.get("NEO4J_DATABASE") or None
    driver = driver_factory(uri, auth=(user, password))
    session_kwargs = {"database": database} if database else {}
    try:
        if hasattr(driver, "verify_connectivity"):
            driver.verify_connectivity()
        with driver.session(**session_kwargs) as session:
            database_row = session.run(
                "CALL db.info() YIELD name "
                "RETURN name AS database_name"
            ).single()
            node_row = session.run(
                "MATCH (n) RETURN count(n) AS node_count"
            ).single()
            relationship_row = session.run(
                "MATCH ()-[r]->() "
                "RETURN count(r) AS relationship_count"
            ).single()
    except Exception as error:
        raise StagingLoadBlocked(
            f"READONLY_TARGET_VERIFICATION_FAILED:{type(error).__name__}"
        ) from error
    finally:
        driver.close()

    runtime_database = str(database_row["database_name"])
    report = {
        "schema_version": "0.1",
        "status": "PASS_READONLY_NONPRODUCTION_TARGET_VERIFIED",
        "source_release_id": plan["manifest"]["source_release_id"],
        "source_plan_id": plan["manifest"]["plan_id"],
        "target_classification": (
            "EXPLICIT_NONPRODUCTION_CONFIGURATION"
        ),
        "runtime_database": runtime_database,
        "configured_database_matches_runtime": (
            database is None or database == runtime_database
        ),
        "current_node_count": int(node_row["node_count"]),
        "current_relationship_count": int(
            relationship_row["relationship_count"]
        ),
        "neo4j_connections": 1,
        "neo4j_reads": 3,
        "neo4j_writes": 0,
        "secrets_emitted": False,
        "eligible_for_dictionary_staging_write": True,
        "eligible_for_production_execution": False,
    }
    if not report["configured_database_matches_runtime"]:
        raise StagingLoadBlocked("CONFIGURED_DATABASE_RUNTIME_MISMATCH")

    evidence_path = Path(evidence_path).resolve()
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan-dir", required=True, type=Path)
    parser.add_argument(
        "--preflight-summary",
        required=True,
        type=Path,
    )
    parser.add_argument("--env-file", type=Path, default=Path(".env"))
    parser.add_argument(
        "--evidence-dir",
        type=Path,
        default=Path("out/unified_program/staging_evidence"),
    )
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument(
        "--execute-staging",
        action="store_true",
        help="Perform the explicitly gated non-production write.",
    )
    parser.add_argument(
        "--verify-target-runtime",
        action="store_true",
        help="Run only the gated read-only endpoint verification.",
    )
    parser.add_argument(
        "--runtime-evidence",
        type=Path,
        default=Path(
            "out/unified_program/staging_evidence/"
            "neo4j_runtime_readonly_verification.json"
        ),
    )
    parser.add_argument(
        "--rollback-snapshot",
        type=Path,
        help="Restore one exact preload snapshot on non-production.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        selected_mutations = sum(
            bool(value)
            for value in (
                args.execute_staging,
                args.verify_target_runtime,
                args.rollback_snapshot,
            )
        )
        if selected_mutations > 1:
            raise StagingLoadBlocked(
                "execute_verify_and_rollback_are_mutually_exclusive"
            )
        if args.rollback_snapshot:
            report = rollback_staging_load(
                args.rollback_snapshot,
                args.env_file,
                args.evidence_dir,
                args.batch_size,
            )
        elif args.execute_staging:
            report = execute_staging_load(
                args.plan_dir,
                args.preflight_summary,
                args.env_file,
                args.evidence_dir,
                args.batch_size,
            )
        elif args.verify_target_runtime:
            report = verify_runtime_target(
                args.plan_dir,
                args.preflight_summary,
                args.env_file,
                args.runtime_evidence,
            )
        else:
            report = inspect_execution_readiness(
                args.plan_dir,
                args.preflight_summary,
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
