# -*- coding: utf-8 -*-
"""Run the complete zero-write dictionary and chunk-context preflight."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from chunk_context_migration_audit import create_chunk_context_audit
from dictionary_release_acceptance import validate_package
from dictionary_release_adapter import build_graph_plan
from dictionary_staging_dry_run import create_staging_dry_run


PREFLIGHT_VERSION = "0.1"


def run_unified_preflight(
    package_dir: Path,
    schema_path: Path,
    queue_path: Path,
    baseline_path: Path,
    linking_stats_path: Path,
    chunk_manifest_path: Path,
    output_root: Path,
) -> dict[str, Any]:
    """Execute all local validation stages without network or DB access."""
    package_dir = Path(package_dir).resolve()
    schema_path = Path(schema_path).resolve()
    output_root = Path(output_root).resolve()
    graph_plan_dir = output_root / "dictionary_graph_plan"
    chunk_audit_dir = output_root / "chunk_context"

    acceptance = validate_package(package_dir, schema_path)
    acceptance_path = output_root / "dictionary_acceptance.json"
    output_root.mkdir(parents=True, exist_ok=True)
    acceptance_path.write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if not str(acceptance.get("status", "")).startswith("PASS_"):
        report = {
            "schema_version": "0.1",
            "preflight_version": PREFLIGHT_VERSION,
            "status": "BLOCKED_DICTIONARY_ACCEPTANCE_FAILED",
            "package_dir": str(package_dir),
            "acceptance_status": acceptance.get("status"),
            "errors": acceptance.get("errors", []),
            "automatic_promotions": 0,
            "neo4j_connections": 0,
            "neo4j_reads": 0,
            "neo4j_writes": 0,
            "eligible_for_staging_target_verification": False,
        }
        (output_root / "unified_preflight_summary.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report

    graph_plan = build_graph_plan(
        package_dir,
        schema_path,
        graph_plan_dir,
    )
    graph_manifest_path = Path(graph_plan["manifest_path"])
    graph_manifest = json.loads(
        graph_manifest_path.read_text(encoding="utf-8")
    )
    marker = ".preview" if graph_manifest.get("preview") else ""
    dry_run_path = (
        output_root / f"dictionary_staging_dry_run{marker}.json"
    )
    dry_run = create_staging_dry_run(
        graph_plan_dir,
        dry_run_path,
    )
    chunk_audit = create_chunk_context_audit(
        graph_plan_dir,
        queue_path,
        baseline_path,
        linking_stats_path,
        chunk_manifest_path,
        chunk_audit_dir,
    )

    preview = bool(graph_manifest.get("preview"))
    clean = (
        not acceptance.get("errors")
        and (
            graph_manifest.get("preview")
            or acceptance.get("canonical_source_resolved")
        )
        and not dry_run.get("errors")
        and graph_plan.get("neo4j_writes") == 0
        and dry_run["execution_controls"]["neo4j_writes"] == 0
        and chunk_audit["controls"]["neo4j_writes"] == 0
    )
    if not clean:
        status = "BLOCKED_UNIFIED_PREFLIGHT_FAILED"
    elif preview:
        status = "PASS_PREVIEW_PROOF_NOT_LOADABLE"
    else:
        status = "PASS_CANONICAL_READY_FOR_STAGING_TARGET_PREFLIGHT"

    report = {
        "schema_version": "0.1",
        "preflight_version": PREFLIGHT_VERSION,
        "status": status,
        "package_dir": str(package_dir),
        "source_release_id": graph_manifest["source_release_id"],
        "source_manifest_status": graph_manifest[
            "source_manifest_status"
        ],
        "preview": preview,
        "stages": {
            "dictionary_acceptance": acceptance["status"],
            "graph_plan": graph_plan["status"],
            "staging_dry_run": dry_run["status"],
            "chunk_context_audit": chunk_audit["status"],
        },
        "counts": {
            "dictionary_records": acceptance["counts"][
                "glossary_records"
            ],
            "graph_nodes": dry_run["counts"]["nodes_to_merge"],
            "graph_relationships": dry_run["counts"][
                "relationships_to_merge"
            ],
            "dictionary_relation_candidates_quarantined": (
                dry_run["counts"]["relation_candidates_quarantined"]
            ),
            "chunk_relation_candidates_quarantined": (
                chunk_audit["legacy_inventory"][
                    "queued_relation_candidates"
                ]
            ),
            "dry_run_errors": dry_run["counts"]["dry_run_errors"],
            "records_rejected": dry_run["counts"][
                "records_rejected"
            ],
        },
        "artifacts": {
            "acceptance": str(acceptance_path),
            "graph_plan_manifest": str(graph_manifest_path),
            "staging_dry_run": str(dry_run_path),
            "chunk_context_audit": str(
                next(
                    chunk_audit_dir.glob(
                        "chunk_context_migration_audit*.json"
                    )
                )
            ),
        },
        "remaining_before_dictionary_staging_load": (
            [
                "CANONICAL_RELEASE_REQUIRED",
                "NONPRODUCTION_TARGET_VERIFICATION_REQUIRED",
                "PRELOAD_TOUCHED_KEY_SNAPSHOT_REQUIRED",
            ]
            if preview
            else [
                "NONPRODUCTION_TARGET_VERIFICATION_REQUIRED",
                "PRELOAD_TOUCHED_KEY_SNAPSHOT_REQUIRED",
            ]
        ),
        "remaining_before_chunk_context_load": chunk_audit[
            "blockers_for_chunk_context_load"
        ],
        "automatic_promotions": 0,
        "neo4j_connections": 0,
        "neo4j_reads": 0,
        "neo4j_writes": 0,
        "eligible_for_staging_target_verification": (
            clean and not preview
        ),
        "eligible_for_production_execution": False,
    }
    (output_root / "unified_preflight_summary.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package-dir", required=True, type=Path)
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path("data/official_glossary/schema.json"),
    )
    parser.add_argument(
        "--queue",
        type=Path,
        default=Path("data/concept_relationships_queue.json"),
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        default=Path("out/neo4j_baseline_stats.json"),
    )
    parser.add_argument(
        "--linking-stats",
        type=Path,
        default=Path("out/linking_stats.json"),
    )
    parser.add_argument(
        "--chunk-manifest",
        type=Path,
        default=Path("out/manifest.json"),
    )
    parser.add_argument("--output-root", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_unified_preflight(
        args.package_dir,
        args.schema,
        args.queue,
        args.baseline,
        args.linking_stats,
        args.chunk_manifest,
        args.output_root,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
