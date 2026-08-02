# -*- coding: utf-8 -*-
"""Create a write-free chunk-to-dictionary graph plan."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from chunk_release_acceptance import validate_chunk_package
from dictionary_release_acceptance import sha256_file


PLANNER_VERSION = "0.1"


class ChunkPlanRejected(RuntimeError):
    """Raised when a canonical chunk plan cannot be built safely."""


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8-sig").splitlines()
        if line.strip()
    ]


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


def _dictionary_nodes_path(plan_dir: Path) -> Path:
    paths = sorted(plan_dir.glob("dictionary_nodes*.jsonl"))
    if len(paths) != 1:
        raise ChunkPlanRejected(
            f"dictionary_nodes_artifact_count:{len(paths)}"
        )
    return paths[0]


def build_chunk_context_plan(
    chunk_package_dir: Path,
    dictionary_plan_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    """Build a deterministic card-id graph plan with no database access."""
    chunk_package_dir = Path(chunk_package_dir).resolve()
    dictionary_plan_dir = Path(dictionary_plan_dir).resolve()
    output_dir = Path(output_dir).resolve()
    acceptance = validate_chunk_package(chunk_package_dir)
    if acceptance["status"] != "PASS_CANONICAL_CHUNK_PACKAGE_ACCEPTED":
        raise ChunkPlanRejected(
            "chunk_package_rejected:"
            + ";".join(acceptance["errors"])
        )

    dictionary_nodes_path = _dictionary_nodes_path(
        dictionary_plan_dir
    )
    dictionary_nodes = _read_jsonl(dictionary_nodes_path)
    known_card_ids = {
        str(row.get("identity_value"))
        for row in dictionary_nodes
        if "GlossaryEntry" in row.get("labels", [])
    }
    chunks = _read_jsonl(chunk_package_dir / "chunks.jsonl")
    relationships = _read_jsonl(
        chunk_package_dir / "chunk_relationships.jsonl"
    )

    missing_cards = sorted(
        {
            str(row.get("card_id"))
            for row in relationships
            if row.get("card_id") not in known_card_ids
        }
    )
    if missing_cards:
        raise ChunkPlanRejected(
            "missing_dictionary_card_ids:" + ",".join(missing_cards)
        )

    nodes = [
        {
            "node_key": f"Chunk:{row['chunk_id']}",
            "labels": ["Chunk"],
            "identity_property": "chunk_id",
            "identity_value": row["chunk_id"],
            "properties": row,
        }
        for row in chunks
    ]
    edges = [
        {
            "edge_id": row["edge_id"],
            "source_node_key": f"Chunk:{row['chunk_id']}",
            "target_node_key": f"GlossaryEntry:{row['card_id']}",
            "relation_type": row["relation_type"],
            "properties": {
                key: value
                for key, value in row.items()
                if key not in {"edge_id", "chunk_id", "card_id"}
            },
        }
        for row in relationships
    ]
    nodes.sort(key=lambda row: row["node_key"])
    edges.sort(key=lambda row: row["edge_id"])

    output_dir.mkdir(parents=True, exist_ok=True)
    nodes_path = output_dir / "chunk_nodes.jsonl"
    edges_path = output_dir / "chunk_dictionary_edges.jsonl"
    nodes_path.write_bytes(_jsonl_bytes(nodes))
    edges_path.write_bytes(_jsonl_bytes(edges))

    seed = (
        f"{PLANNER_VERSION}|{acceptance['manifest_sha256']}|"
        f"{sha256_file(dictionary_nodes_path)}"
    ).encode("utf-8")
    plan_id = (
        "CHUNKPLAN-" + hashlib.sha256(seed).hexdigest()[:16].upper()
    )
    relation_counts = Counter(
        row["relation_type"] for row in relationships
    )
    manifest = {
        "schema_version": "0.1",
        "planner_version": PLANNER_VERSION,
        "status": "PASS_WRITE_FREE_CHUNK_GRAPH_PLAN",
        "plan_id": plan_id,
        "dictionary_release_id": acceptance[
            "dictionary_release_id"
        ],
        "source_chunk_manifest_sha256": acceptance[
            "manifest_sha256"
        ],
        "source_dictionary_nodes_sha256": sha256_file(
            dictionary_nodes_path
        ),
        "counts": {
            "chunk_nodes": len(nodes),
            "chunk_dictionary_edges": len(edges),
            "relationship_type_counts": dict(
                sorted(relation_counts.items())
            ),
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
            "all_card_endpoints_exist": True,
            "pending_context_queue_included": 0,
            "automatic_promotions": 0,
            "neo4j_connections": 0,
            "neo4j_reads": 0,
            "neo4j_writes": 0,
        },
        "required_load_predecessor": (
            f"DICTIONARY_RELEASE:{acceptance['dictionary_release_id']}"
        ),
        "eligible_for_write_free_dry_run": True,
        "eligible_for_staging_execution": False,
        "eligible_for_production_execution": False,
    }
    manifest_path = output_dir / "chunk_graph_plan_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunk-package", required=True, type=Path)
    parser.add_argument(
        "--dictionary-plan",
        required=True,
        type=Path,
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_chunk_context_plan(
            args.chunk_package,
            args.dictionary_plan,
            args.output_dir,
        )
    except ChunkPlanRejected as error:
        print(
            json.dumps(
                {
                    "status": "BLOCKED",
                    "error": str(error),
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
