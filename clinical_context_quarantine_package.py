# -*- coding: utf-8 -*-
"""Build a durable, de-identified quarantine package for chunk context."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from dictionary_release_acceptance import sha256_file


EMAIL_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+972[- ]?|0)(?:[23489]|5\d)[- ]?\d{3}[- ]?\d{4}(?!\d)"
)
ISRAELI_ID_PATTERN = re.compile(r"(?<!\d)\d{9}(?!\d)")
CHUNK_ID_PATTERN = re.compile(r"^[a-f0-9]{24}$")
CARD_ID_PATTERN = re.compile(r"^[A-H][0-9]{3}$")
ALLOWED_RELATION_TYPES = {
    "IS_SYMPTOM_OF",
    "LEADS_TO",
    "PREVENTS",
    "IS_RECOMMENDED_FOR",
    "IS_CONTRAINDICATED_FOR",
}


class ContextQuarantineBlocked(RuntimeError):
    """Raised when context evidence cannot be packaged safely."""


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
            raise ContextQuarantineBlocked(
                f"{path.name}:{line_number}:invalid_json"
            ) from error
        if not isinstance(row, dict):
            raise ContextQuarantineBlocked(
                f"{path.name}:{line_number}:not_object"
            )
        rows.append(row)
    return rows


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


def _pii_findings(text: str) -> list[str]:
    return [
        label
        for label, pattern in (
            ("email", EMAIL_PATTERN),
            ("phone", PHONE_PATTERN),
            ("israeli_id_candidate", ISRAELI_ID_PATTERN),
        )
        if pattern.search(text)
    ]


def _artifact(path: Path, count: int) -> dict[str, Any]:
    return {
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "record_count": count,
    }


def build_context_quarantine_package(
    queue_path: Path,
    provenance_path: Path,
    output_dir: Path,
    dictionary_release_id: str,
) -> dict[str, Any]:
    """Preserve all context evidence without promoting semantic edges."""
    queue_path = Path(queue_path).resolve()
    provenance_path = Path(provenance_path).resolve()
    output_dir = Path(output_dir).resolve()
    if not dictionary_release_id.startswith(("D4-", "RELEASE-")):
        raise ContextQuarantineBlocked(
            "CANONICAL_DICTIONARY_RELEASE_REQUIRED"
        )
    queue = _read_json(queue_path)
    provenance = _read_jsonl(provenance_path)
    if not isinstance(queue, list):
        raise ContextQuarantineBlocked("QUEUE_NOT_ARRAY")
    if len(queue) != len(provenance):
        raise ContextQuarantineBlocked(
            "QUEUE_PROVENANCE_COUNT_MISMATCH"
        )
    provenance_by_row = {
        int(row["source_row_number"]): row for row in provenance
    }
    if len(provenance_by_row) != len(provenance):
        raise ContextQuarantineBlocked(
            "DUPLICATE_PROVENANCE_SOURCE_ROW"
        )

    excerpts_by_chunk: dict[str, dict[str, Any]] = {}
    candidates: list[dict[str, Any]] = []
    errors: list[str] = []
    pair_counts: Counter[str] = Counter()
    for row_number, source in enumerate(queue, start=1):
        provenance_row = provenance_by_row.get(row_number)
        if provenance_row is None:
            errors.append(f"row:{row_number}:provenance_missing")
            continue
        chunk_id = str(source.get("chunk_id", ""))
        quote = str(source.get("quote", ""))
        quote_sha = hashlib.sha256(quote.encode("utf-8")).hexdigest()
        if not CHUNK_ID_PATTERN.fullmatch(chunk_id):
            errors.append(f"row:{row_number}:invalid_chunk_id")
        if not quote:
            errors.append(f"row:{row_number}:missing_quote")
        for finding in _pii_findings(quote):
            errors.append(f"row:{row_number}:pii:{finding}")
        if provenance_row.get("chunk_id") != chunk_id:
            errors.append(f"row:{row_number}:chunk_id_mismatch")
        if provenance_row.get("evidence_quote_sha256") != quote_sha:
            errors.append(f"row:{row_number}:quote_hash_mismatch")
        if provenance_row.get("automatic_promotion") is not False:
            errors.append(f"row:{row_number}:automatic_promotion")
        if provenance_row.get(
            "included_in_relation_candidates_csv"
        ) is not False:
            errors.append(f"row:{row_number}:unexpected_promotion")
        relation_type = str(provenance_row.get("relation_type", ""))
        if relation_type not in ALLOWED_RELATION_TYPES:
            errors.append(f"row:{row_number}:invalid_relation_type")

        excerpt = {
            "evidence_id": f"CHUNKEXCERPT-{chunk_id.upper()}",
            "source_chunk_id": chunk_id,
            "deidentified_excerpt": quote,
            "excerpt_sha256": quote_sha,
            "excerpt_length": len(quote),
            "incomplete_chunk": True,
            "deidentification_status": "PASS",
            "data_classification": "NO_PATIENT_DATA",
        }
        existing = excerpts_by_chunk.get(chunk_id)
        if existing and existing != excerpt:
            errors.append(f"row:{row_number}:chunk_excerpt_conflict")
        excerpts_by_chunk[chunk_id] = excerpt

        source_ids = [
            str(item)
            for item in provenance_row.get("concept_a_card_ids", [])
        ]
        target_ids = [
            str(item)
            for item in provenance_row.get("concept_b_card_ids", [])
        ]
        for card_id in source_ids + target_ids:
            if not CARD_ID_PATTERN.fullmatch(card_id):
                errors.append(
                    f"row:{row_number}:invalid_card_id:{card_id}"
                )
        pair_status = str(
            provenance_row.get("pair_mapping_status", "")
        )
        pair_counts[pair_status] += 1
        candidates.append(
            {
                "candidate_id": provenance_row["candidate_id"],
                "source_row_number": row_number,
                "source_chunk_id": chunk_id,
                "evidence_id": excerpt["evidence_id"],
                "relation_type": relation_type,
                "source_legacy_label": provenance_row.get(
                    "concept_a_source_label"
                ),
                "target_legacy_label": provenance_row.get(
                    "concept_b_source_label"
                ),
                "source_card_ids": source_ids,
                "target_card_ids": target_ids,
                "pair_mapping_status": pair_status,
                "quarantine_status": (
                    "READY_FOR_SEMANTIC_REVIEW"
                    if pair_status == "BOTH_ENDPOINTS_UNIQUE"
                    else "BLOCKED_UNMAPPED_ENDPOINT"
                ),
                "eligible_for_canonical_relation": False,
                "automatic_promotion": False,
                "dictionary_release_id": dictionary_release_id,
            }
        )

    unique_errors = sorted(set(errors))
    if unique_errors:
        raise ContextQuarantineBlocked(";".join(unique_errors[:20]))

    excerpts = sorted(
        excerpts_by_chunk.values(),
        key=lambda row: row["source_chunk_id"],
    )
    candidates.sort(key=lambda row: row["candidate_id"])
    output_dir.mkdir(parents=True, exist_ok=True)
    excerpts_path = output_dir / "context_evidence_excerpts.jsonl"
    candidates_path = (
        output_dir / "clinical_context_relation_candidates.jsonl"
    )
    excerpts_path.write_bytes(_jsonl_bytes(excerpts))
    candidates_path.write_bytes(_jsonl_bytes(candidates))

    seed = (
        f"{dictionary_release_id}|{sha256_file(excerpts_path)}|"
        f"{sha256_file(candidates_path)}"
    ).encode("utf-8")
    release_id = (
        "CONTEXTQUARANTINE-"
        + hashlib.sha256(seed).hexdigest()[:16].upper()
    )
    manifest = {
        "schema_version": "0.1",
        "manifest_status": "CANONICAL_CONTEXT_QUARANTINE_EXPORT",
        "release_id": release_id,
        "dictionary_release_id": dictionary_release_id,
        "record_counts": {
            "evidence_excerpts": len(excerpts),
            "relation_candidates": len(candidates),
            "both_endpoints_unique": pair_counts[
                "BOTH_ENDPOINTS_UNIQUE"
            ],
            "partially_mapped": pair_counts["PARTIALLY_MAPPED"],
        },
        "artifacts": {
            excerpts_path.name: _artifact(
                excerpts_path,
                len(excerpts),
            ),
            candidates_path.name: _artifact(
                candidates_path,
                len(candidates),
            ),
        },
        "controls": {
            "excerpts_are_incomplete_chunks": True,
            "direct_identifier_findings": 0,
            "canonical_semantic_relations": 0,
            "automatic_promotions": 0,
            "llm_use": 0,
            "api_key_use": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        },
        "eligible_for_quarantine_graph_plan": True,
        "eligible_for_canonical_relation_load": False,
        "eligible_for_production_execution": False,
    }
    manifest_path = output_dir / "context_quarantine_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "status": "PASS_CONTEXT_QUARANTINE_PACKAGE_CREATED",
        "release_id": release_id,
        "dictionary_release_id": dictionary_release_id,
        "counts": manifest["record_counts"],
        "manifest_path": str(manifest_path),
        "automatic_promotions": 0,
        "neo4j_connections": 0,
        "neo4j_writes": 0,
        "eligible_for_quarantine_graph_plan": True,
        "eligible_for_canonical_relation_load": False,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dictionary-release-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = build_context_quarantine_package(
            args.queue,
            args.provenance,
            args.output_dir,
            args.dictionary_release_id,
        )
    except ContextQuarantineBlocked as error:
        report = {
            "status": "BLOCKED_CONTEXT_QUARANTINE_PACKAGE",
            "error": str(error),
            "automatic_promotions": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
