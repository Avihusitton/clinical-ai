# -*- coding: utf-8 -*-
"""Reconstruct queued chunk endpoints from local source documents, write-free."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import types
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from dictionary_release_acceptance import sha256_file


EMAIL_PATTERN = re.compile(
    r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(
    r"(?<!\d)(?:\+972[- ]?|0)(?:[23489]|5\d)[- ]?\d{3}[- ]?\d{4}(?!\d)"
)
ISRAELI_ID_PATTERN = re.compile(r"(?<!\d)\d{9}(?!\d)")


class ChunkReconstructionBlocked(RuntimeError):
    """Raised when a canonical durable export cannot be produced safely."""


def _load_ingestion_components() -> Any:
    """Import parsing/chunking code while making LLM use impossible."""
    blocked_llm = types.ModuleType("llm_client")

    class BlockedLLM:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            raise ChunkReconstructionBlocked("LLM_USE_FORBIDDEN")

    blocked_llm.LLMClient = BlockedLLM
    blocked_llm.LLMError = ChunkReconstructionBlocked
    sys.modules["llm_client"] = blocked_llm
    import ingestion_pipeline

    return ingestion_pipeline


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
    return (("\n".join(lines) + "\n") if lines else "").encode(
        "utf-8"
    )


def _source_files(roots: list[Path]) -> list[Path]:
    files: set[Path] = set()
    for root in roots:
        root = root.resolve()
        if not root.is_dir():
            continue
        for suffix in ("*.docx", "*.pdf"):
            for path in root.rglob(suffix):
                if path.is_file() and not path.name.startswith("~$"):
                    files.add(path.resolve())
    return sorted(files, key=lambda path: str(path).casefold())


def _direct_identifier_findings(text: str) -> list[str]:
    findings: list[str] = []
    for label, pattern in (
        ("email", EMAIL_PATTERN),
        ("phone", PHONE_PATTERN),
        ("israeli_id_candidate", ISRAELI_ID_PATTERN),
    ):
        if pattern.search(text):
            findings.append(label)
    return findings


def _queue_by_chunk(queue: list[dict[str, Any]]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = defaultdict(list)
    for row in queue:
        chunk_id = str(row.get("chunk_id", ""))
        if re.fullmatch(r"[a-f0-9]{24}", chunk_id):
            grouped[chunk_id].append(row)
    return dict(grouped)


def _read_and_chunk(path: Path, components: Any, cfg: Any) -> list[Any]:
    if path.suffix.lower() == ".pdf":
        paragraphs = components.PdfReader.read(path)
        metadata = {}
    else:
        paragraphs, metadata = components.DocxReader.read(path)
    if not paragraphs:
        return []
    content_hash = components.DocxReader.content_hash(paragraphs)
    doc_type = components.DocumentTypeClassifier.classify(
        paragraphs,
        metadata,
        cfg,
    )
    if doc_type == components.DocumentType.OFFICIAL_METHOD_DOC:
        return components.chunk_by_headings(
            path.stem,
            content_hash,
            paragraphs,
            cfg,
        )
    detector = components.TimeAnchorDetector(cfg)
    chunks, _, _ = components.Chunker(
        cfg,
        detector,
    ).chunk_document(path.stem, content_hash, paragraphs)
    return chunks


def _chunk_row(
    chunk: Any,
    source_path: Path,
    source_sha256: str,
    document_type: str,
) -> dict[str, Any]:
    text = str(chunk.text)
    return {
        "chunk_id": chunk.chunk_id,
        "doc_id": chunk.doc_id,
        "source_document_id": (
            f"SRC-{source_sha256[:16].upper()}"
        ),
        "source_file_sha256": source_sha256,
        "text_sha256": hashlib.sha256(
            text.encode("utf-8")
        ).hexdigest(),
        "deidentified_text": text,
        "paragraph_range": list(chunk.paragraph_range),
        "lesson_number": chunk.lesson_number,
        "lesson_date": (
            chunk.lesson_date.isoformat()
            if chunk.lesson_date
            else None
        ),
        "temporal_status": chunk.temporal_status.value,
        "modality": "general",
        "heading_path": list(chunk.heading_path),
        "source_authority": (
            "METHOD_PRIMARY"
            if document_type == "official_method_doc"
            else "SECONDARY_OR_TRANSCRIPT"
        ),
        "deidentification_status": "PASS",
        "deidentification_method": (
            "EXACT_LEGACY_CHUNK_ID_AND_QUEUE_EXCERPT_MATCH_"
            "PLUS_DIRECT_IDENTIFIER_SCREEN"
        ),
        "data_classification": "NO_PATIENT_DATA",
        "source_filename": source_path.name,
    }


def _artifact_entry(path: Path, record_count: int) -> dict[str, Any]:
    return {
        "sha256": sha256_file(path),
        "bytes": path.stat().st_size,
        "record_count": record_count,
    }


def reconstruct_durable_chunk_package(
    queue_path: Path,
    source_roots: list[Path],
    output_dir: Path,
    dictionary_release_id: str,
) -> dict[str, Any]:
    """Reconstruct only exact target chunks and emit a canonical package."""
    queue_path = Path(queue_path).resolve()
    output_dir = Path(output_dir).resolve()
    queue = _read_json(queue_path)
    if not isinstance(queue, list):
        raise ChunkReconstructionBlocked("QUEUE_NOT_ARRAY")
    target_rows = _queue_by_chunk(queue)
    target_ids = set(target_rows)
    if not target_ids:
        raise ChunkReconstructionBlocked("NO_VALID_TARGET_CHUNK_IDS")
    if not str(dictionary_release_id).startswith(("D4-", "RELEASE-")):
        raise ChunkReconstructionBlocked(
            "CANONICAL_DICTIONARY_RELEASE_REQUIRED"
        )

    components = _load_ingestion_components()
    cfg = components.Config()
    matched: dict[str, list[tuple[Any, Path, str]]] = defaultdict(list)
    scan_errors: list[dict[str, str]] = []
    files = _source_files(source_roots)
    for path in files:
        try:
            chunks = _read_and_chunk(path, components, cfg)
        except Exception as error:
            scan_errors.append(
                {
                    "source_filename": path.name,
                    "error_type": type(error).__name__,
                }
            )
            continue
        document_type = (
            "official_method_doc"
            if chunks and chunks[0].heading_path
            else "lesson_transcript"
        )
        for chunk in chunks:
            if chunk.chunk_id in target_ids:
                matched[chunk.chunk_id].append(
                    (chunk, path, document_type)
                )

    missing = sorted(target_ids - set(matched))
    ambiguous = sorted(
        chunk_id
        for chunk_id, candidates in matched.items()
        if len(
            {
                hashlib.sha256(
                    str(candidate[0].text).encode("utf-8")
                ).hexdigest()
                for candidate in candidates
            }
        )
        > 1
    )
    rows: list[dict[str, Any]] = []
    excerpt_mismatches: list[str] = []
    identifier_findings: dict[str, list[str]] = {}
    duplicate_source_matches: dict[str, int] = {}
    for chunk_id in sorted(matched):
        candidates = sorted(
            matched[chunk_id],
            key=lambda item: str(item[1]).casefold(),
        )
        chunk, path, document_type = candidates[0]
        duplicate_source_matches[chunk_id] = len(candidates)
        source_sha = sha256_file(path)
        row = _chunk_row(
            chunk,
            path,
            source_sha,
            document_type,
        )
        queue_quotes = {
            str(item.get("quote", ""))
            for item in target_rows[chunk_id]
            if item.get("quote")
        }
        if (
            len(queue_quotes) != 1
            or not row["deidentified_text"].startswith(
                next(iter(queue_quotes), "")
            )
        ):
            excerpt_mismatches.append(chunk_id)
        findings = _direct_identifier_findings(
            row["deidentified_text"]
        )
        if findings:
            identifier_findings[chunk_id] = findings
        rows.append(row)

    blockers: list[str] = []
    if missing:
        blockers.append("TARGET_CHUNKS_MISSING")
    if ambiguous:
        blockers.append("AMBIGUOUS_CHUNK_RECONSTRUCTION")
    if excerpt_mismatches:
        blockers.append("QUEUE_EXCERPT_MISMATCH")
    if identifier_findings:
        blockers.append("DIRECT_IDENTIFIER_FINDINGS")

    report = {
        "schema_version": "0.1",
        "status": (
            "PASS_EXACT_DURABLE_CHUNK_RECONSTRUCTION"
            if not blockers
            else "BLOCKED_DURABLE_CHUNK_RECONSTRUCTION"
        ),
        "dictionary_release_id": dictionary_release_id,
        "queue_path": str(queue_path),
        "source_roots": [str(Path(root).resolve()) for root in source_roots],
        "counts": {
            "source_files_scanned": len(files),
            "source_file_read_errors": len(scan_errors),
            "target_chunk_ids": len(target_ids),
            "matched_chunk_ids": len(matched),
            "missing_chunk_ids": len(missing),
            "ambiguous_chunk_ids": len(ambiguous),
            "queue_excerpt_mismatches": len(excerpt_mismatches),
            "chunks_with_direct_identifier_findings": len(
                identifier_findings
            ),
        },
        "missing_chunk_ids": missing,
        "ambiguous_chunk_ids": ambiguous,
        "queue_excerpt_mismatch_ids": sorted(excerpt_mismatches),
        "identifier_finding_labels_by_chunk": identifier_findings,
        "duplicate_source_match_counts": {
            key: value
            for key, value in sorted(duplicate_source_matches.items())
            if value > 1
        },
        "scan_error_types": dict(
            sorted(
                {
                    item["error_type"]: sum(
                        row["error_type"] == item["error_type"]
                        for row in scan_errors
                    )
                    for item in scan_errors
                }.items()
            )
        ),
        "controls": {
            "llm_use": 0,
            "api_key_use": 0,
            "neo4j_connections": 0,
            "neo4j_reads": 0,
            "neo4j_writes": 0,
            "raw_text_emitted_when_blocked": False,
        },
        "blockers": blockers,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "chunk_reconstruction_report.json"

    if blockers:
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return report

    chunks_path = output_dir / "chunks.jsonl"
    relationships_path = output_dir / "chunk_relationships.jsonl"
    chunks_path.write_bytes(_jsonl_bytes(rows))
    relationships_path.write_bytes(b"")
    release_seed = (
        f"{dictionary_release_id}|{sha256_file(chunks_path)}|"
        f"{len(rows)}"
    ).encode("utf-8")
    chunk_release_id = (
        "CHUNKRELEASE-"
        + hashlib.sha256(release_seed).hexdigest()[:16].upper()
    )
    manifest = {
        "schema_version": "0.1",
        "release_id": chunk_release_id,
        "dictionary_release_id": dictionary_release_id,
        "manifest_status": "CANONICAL_CHUNK_EXPORT",
        "record_counts": {
            "chunks": len(rows),
            "chunk_relationships": 0,
        },
        "artifacts": {
            chunks_path.name: _artifact_entry(chunks_path, len(rows)),
            relationships_path.name: _artifact_entry(
                relationships_path,
                0,
            ),
        },
        "controls": {
            "source_data_classification": "NO_PATIENT_DATA",
            "deidentification_status": "PASS",
            "exact_legacy_chunk_id_matches": len(rows),
            "queue_excerpt_matches": len(rows),
            "direct_identifier_findings": 0,
            "automatic_promotions": 0,
            "llm_use": 0,
            "api_key_use": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        },
        "eligible_for_chunk_package_acceptance": True,
        "eligible_for_production_execution": False,
    }
    manifest_path = output_dir / "chunk_release_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    report["release_id"] = chunk_release_id
    report["artifacts"] = {
        "manifest": str(manifest_path),
        "chunks": str(chunks_path),
        "relationships": str(relationships_path),
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--queue", required=True, type=Path)
    parser.add_argument(
        "--source-root",
        required=True,
        action="append",
        type=Path,
    )
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dictionary-release-id", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        report = reconstruct_durable_chunk_package(
            args.queue,
            args.source_root,
            args.output_dir,
            args.dictionary_release_id,
        )
    except ChunkReconstructionBlocked as error:
        report = {
            "status": "BLOCKED_DURABLE_CHUNK_RECONSTRUCTION",
            "error": str(error),
            "llm_use": 0,
            "api_key_use": 0,
            "neo4j_connections": 0,
            "neo4j_writes": 0,
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
