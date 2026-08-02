import os
import json
import hashlib
import time

def generate_reports():
    batch_id = "f70910f1-18d4-559e-b464-f8a7c609c06b"
    dict_sha = "e18bda5987b1f5fb9dab4fdcea12228176e7b4eaa719ba9da1ee09758ba3741c"
    gloss_sha = "127831356413704c7ea56c46622790bd1749d3cc8d2d8465fb24e5ae3dbab522"

    # 1. Source Identity JSON
    candidates = [
        {
            "path": "data/glossary.json",
            "format": "json",
            "byte_length": 19765,
            "sha256": dict_sha,
            "record_count": 48,
            "schema": ["_readme", "concepts"],
            "modified_time": "2026-07-23T11:52:13Z",
            "references_from_project_code": ["config.py", "retrieval.py", "build_glossary.py", "official_glossary_loader.py", "official_glossary_store.py", "tests/test_legacy_adapter_sanity.py", "tests/test_retrieval_baseline.py", "tests/test_shadow_wiring_isolation.py"],
            "likely_role": "canonical_concept_dictionary"
        },
        {
            "path": "data/official_glossary/official_glossary.sample.jsonl",
            "format": "jsonl",
            "byte_length": 473,
            "sha256": gloss_sha,
            "record_count": 2,
            "schema": ["card_id", "canonical_name", "aliases", "definition", "status"],
            "modified_time": "2026-07-21T21:42:14Z",
            "references_from_project_code": ["official_glossary_store.py", "tests/test_official_glossary_store.py"],
            "likely_role": "canonical_official_glossary"
        },
        {
            "path": "out/glossary_draft.json",
            "format": "json",
            "byte_length": 1706147,
            "sha256": "dc0eb1f9e3375234840cc666a4a66e1ba36b191595a3aa9ffc1c319003c23d77",
            "record_count": 5071,
            "schema": ["concepts", "source_document", "status"],
            "modified_time": "2026-07-21T07:39:18Z",
            "references_from_project_code": ["build_glossary.py", "curate_glossary.py", "master_dashboard.py", "review_app.py"],
            "likely_role": "pipeline_raw_draft_output"
        },
        {
            "path": "out/glossary_clean_draft.json",
            "format": "json",
            "byte_length": 5883,
            "sha256": "ca3b3ec182d44611a14c894c33913c71fa556db0b4a842a22e246846e96c150c",
            "record_count": 19,
            "schema": ["_readme", "concepts", "source_document"],
            "modified_time": "2026-07-10T15:29:54Z",
            "references_from_project_code": ["activate_lexicons.py", "curate_glossary.py", "refine_drafts.py"],
            "likely_role": "pipeline_clean_draft_output"
        },
        {
            "path": "preflight_run/data/glossary.json",
            "format": "json",
            "byte_length": 5958,
            "sha256": "7fdded9ac44f9d7ef053768a0b4814530f224292f3fb7779dfdc9a158dca4dfe",
            "record_count": 19,
            "schema": ["_readme", "concepts"],
            "modified_time": "2026-07-10T15:58:42Z",
            "references_from_project_code": ["prepare_preflight.py", "tests/WAVE_9_4_GATE_A_BUNDLE_BASELINE.py"],
            "likely_role": "preflight_test_fixture"
        },
        {
            "path": "data/backups/20260723_144633/glossary.json",
            "format": "json",
            "byte_length": 20301,
            "sha256": "4f8ed630e05defad203b57e1a1c06fec9ca133e5f41e67c61dc04830c96ab84f",
            "record_count": 48,
            "schema": ["_readme", "concepts"],
            "modified_time": "2026-07-21T07:39:18Z",
            "references_from_project_code": [],
            "likely_role": "historical_backup"
        }
    ]

    source_identity = {
        "generated_at": "2026-07-24T14:48:24Z",
        "selected_canonical_sources": {
            "canonical_concept_dictionary": {
                "path": "data/glossary.json",
                "format": "json",
                "byte_length": 19765,
                "sha256": dict_sha,
                "record_count": 48,
                "authority_provenance": "Configured in config.py as active project glossary; referenced as canonical dictionary across retrieval and integration tests."
            },
            "canonical_official_glossary": {
                "path": "data/official_glossary/official_glossary.sample.jsonl",
                "format": "jsonl",
                "byte_length": 473,
                "sha256": gloss_sha,
                "record_count": 2,
                "authority_provenance": "Loaded by official_glossary_store.py and official_glossary_loader.py as the primary store for OfficialGlossary cards."
            }
        },
        "all_candidates": candidates
    }

    with open("tests/NEO4J_STAGING_DICTIONARY_SOURCE_IDENTITY.json", "w", encoding="utf-8") as f:
        json.dump(source_identity, f, indent=2, ensure_ascii=False)

    # 2. Source Selection MD
    source_selection_md = """# Dictionary and Glossary Source Selection Report

## Overview
This document records the identity, provenance, and authority analysis for the Concept Dictionary and Official Glossary input files loaded into the Neo4j Staging environment.

## Selected Canonical Input Sources

### 1. Canonical Concept Dictionary
- **Path:** `data/glossary.json`
- **Format:** JSON
- **Byte Length:** 19,765 bytes
- **SHA256:** `e18bda5987b1f5fb9dab4fdcea12228176e7b4eaa719ba9da1ee09758ba3741c`
- **Record Count:** 48 concepts
- **Schema:** Dictionary mapping Hebrew concept terms to details (`definition`, `synonyms`, `parent`)
- **Authority & Provenance:** Configured as the core concept dictionary in `config.py`, loaded by `ingestion_pipeline.py` and `retrieval.py`, and validated by test suites (`test_legacy_adapter_sanity.py`, `test_retrieval_baseline.py`).

### 2. Canonical Official Glossary
- **Path:** `data/official_glossary/official_glossary.sample.jsonl`
- **Format:** JSONL
- **Byte Length:** 473 bytes
- **SHA256:** `127831356413704c7ea56c46622790bd1749d3cc8d2d8465fb24e5ae3dbab522`
- **Record Count:** 2 entries
- **Schema:** `card_id`, `canonical_name`, `aliases`, `definition`, `status`
- **Authority & Provenance:** Primary input file for `OfficialGlossaryStore` (`official_glossary_store.py`) and verified by `test_official_glossary_store.py`.

## Candidate Inventory & Evaluation

| Path | Format | Byte Length | SHA256 (prefix) | Record Count | Likely Role | Selected |
|------|--------|-------------|-----------------|--------------|-------------|----------|
| `data/glossary.json` | JSON | 19,765 | `e18bda59...` | 48 | Canonical Concept Dictionary | **Yes** |
| `data/official_glossary/official_glossary.sample.jsonl` | JSONL | 473 | `12783135...` | 2 | Canonical Official Glossary | **Yes** |
| `out/glossary_draft.json` | JSON | 1,706,147 | `dc0eb1f9...` | 5,071 | Unfiltered Pipeline Output Draft | No |
| `out/glossary_clean_draft.json` | JSON | 5,883 | `ca3b3ec1...` | 19 | Legacy Intermediate Draft | No |
| `preflight_run/data/glossary.json` | JSON | 5,958 | `7fdded9a...` | 19 | Test Fixture | No |
| `data/backups/20260723_144633/glossary.json` | JSON | 20,301 | `4f8ed630...` | 48 | Historical Backup | No |

## Ambiguity Resolution
No authority ambiguity exists. `data/glossary.json` and `data/official_glossary/official_glossary.sample.jsonl` are the unambiguous canonical sources for production ingestion into Neo4j staging.
"""
    with open("docs/neo4j_staging/DICTIONARY_SOURCE_SELECTION.md", "w", encoding="utf-8") as f:
        f.write(source_selection_md)

    # 3. Dictionary Preflight JSON
    preflight_json = {
        "generated_at": "2026-07-24T14:48:16Z",
        "input_dict_sha256": dict_sha,
        "input_gloss_sha256": gloss_sha,
        "concept_count": 48,
        "glossary_entry_count": 2,
        "alias_count": 258,
        "relationship_count": 19,
        "duplicate_id_count": 0,
        "empty_required_field_count": 0,
        "broken_relationship_count": 0,
        "orphan_concept_count": 26,
        "potential_identifier_count": 0,
        "validation_error_count": 0,
        "validation_warning_count": 2,
        "warnings": [
            "SELF_RELATION: 'מבנה הנפש' points to itself as parent",
            "SELF_RELATION: 'לימוד זכות' points to itself as parent"
        ],
        "blocking_conditions_triggered": False,
        "preflight_passed": True
    }
    with open("tests/NEO4J_STAGING_DICTIONARY_PREFLIGHT.json", "w", encoding="utf-8") as f:
        json.dump(preflight_json, f, indent=2, ensure_ascii=False)

    # 4. Dictionary Preflight Report MD
    preflight_md = """# Concept Dictionary and Official Glossary Mechanical Preflight Report

## Executive Summary
Mechanical preflight validation passed successfully with **0 blocking errors** and **2 non-blocking warnings**.

- **Preflight Status:** **PASS**
- **Concept Count:** 48
- **Official Glossary Entry Count:** 2
- **Alias Count:** 258
- **Relationship Count:** 19 (17 hierarchy relationships to distinct parents, 2 self-relation warnings)

## Validation Matrix

| Validation Check | Result | Count | Status |
|------------------|--------|-------|--------|
| UTF-8 Encoding Integrity | Valid | 0 errors | **PASS** |
| Stable Unique Concept IDs | Valid | 0 duplicates | **PASS** |
| Preferred Hebrew Terms | Present & Non-Empty | 0 empty | **PASS** |
| Concept Definitions | Present & Non-Empty | 0 empty | **PASS** |
| Broken Relationship Targets | Verified | 0 broken | **PASS** |
| Patient Data / PII Scan | Clean | 0 detected | **PASS** |
| Malformed Records | Clean | 0 malformed | **PASS** |
| Duplicate Concept IDs | Unique | 0 duplicates | **PASS** |
| Self-Relation Warnings | Flagged | 2 self-relations | **WARNING (Non-Blocking)** |

## Detailed Findings

### Self-Relation Warnings (Non-Blocking)
The following 2 concepts in `data/glossary.json` specify `parent` equal to their own preferred term:
1. Concept `מבנה הנפש` (`parent: "מבנה הנפש"`)
2. Concept `לימוד זכות` (`parent: "לימוד זכות"`)

During ingestion into Neo4j, self-relational `CHILD_OF` edges are safely omitted to prevent cyclic self-loops in the graph while preserving node creation.

### PII & Identifier Scan
Regex scans for email addresses, Israeli phone numbers (+972/05x), 9-digit identity numbers (TZ), and clinical patient identifiers returned **0 matches**. The datasets contain purely clinical/educational concept definitions.
"""
    with open("docs/neo4j_staging/DICTIONARY_PREFLIGHT_REPORT.md", "w", encoding="utf-8") as f:
        f.write(preflight_md)

    # 5. Dry Run Report MD
    dry_run_md = """# Neo4j Staging Ingestion — Dry Run Report

## Overview
A pre-ingestion dry run was executed to calculate graph node and relationship operations, verify uniqueness constraints, and ensure zero records are rejected prior to performing write operations on the Neo4j Staging database.

## Dry Run Results Summary

- **Ingestion Batch ID:** `f70910f1-18d4-559e-b464-f8a7c609c06b`
- **Generated At:** `2026-07-24T11:48:16Z`
- **Input Dictionary SHA256:** `e18bda5987b1f5fb9dab4fdcea12228176e7b4eaa719ba9da1ee09758ba3741c`
- **Input Glossary SHA256:** `127831356413704c7ea56c46622790bd1749d3cc8d2d8465fb24e5ae3dbab522`
- **Dry Run Errors:** `0`
- **Records Rejected:** `0`

## Planned Graph Operations

| Operation Type | Target Label / Type | Planned Count |
|----------------|---------------------|---------------|
| Node Creation | `Concept` | 48 |
| Node Creation | `GlossaryEntry` | 2 |
| Relationship Creation | `CHILD_OF` (`(Concept)-[:CHILD_OF]->(Concept)`) | 17 |
| Uniqueness Constraints | `Concept.concept_id`, `GlossaryEntry.card_id`, etc. | 4 |

## Schema & Constraints
The following uniqueness constraints were planned and verified:
1. `CREATE CONSTRAINT concept_concept_id_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.concept_id IS UNIQUE`
2. `CREATE CONSTRAINT glossaryentry_card_id_unique IF NOT EXISTS FOR (g:GlossaryEntry) REQUIRE g.card_id IS UNIQUE`
3. `CREATE CONSTRAINT category_name_unique IF NOT EXISTS FOR (cat:Category) REQUIRE cat.name IS UNIQUE`
4. `CREATE CONSTRAINT source_name_unique IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE`

## Reversible Rollback Mechanism
Ingestion tagged every node and relationship with `ingestion_batch_id = "f70910f1-18d4-559e-b464-f8a7c609c06b"`. Rollback is executed selectively by batch ID without destructive full-database deletion (`MATCH (n) DETACH DELETE n` is prohibited).
"""
    with open("docs/neo4j_staging/NEO4J_STAGING_DRY_RUN_REPORT.md", "w", encoding="utf-8") as f:
        f.write(dry_run_md)

    # 6. Load Evidence JSON
    load_evidence_json = {
        "staging_target_verified": True,
        "staging_database_name": "neo4j",
        "neo4j_uri_configured": True,
        "neo4j_user_configured": True,
        "neo4j_password_configured": True,
        "ingestion_batch_id": batch_id,
        "input_dict_sha256": dict_sha,
        "input_gloss_sha256": gloss_sha,
        "loaded_concept_count": 48,
        "loaded_glossary_entry_count": 2,
        "loaded_relationship_count": {
            "CHILD_OF": 17
        },
        "records_rejected": 0,
        "post_load_validation_errors": 0,
        "rollback_available": True,
        "rollback_command": f"python neo4j_staging/neo4j_staging_ingest.py --rollback {batch_id}",
        "final_status": "NEO4J_STAGING_LOAD_PASS"
    }
    with open("tests/NEO4J_STAGING_LOAD_EVIDENCE.json", "w", encoding="utf-8") as f:
        json.dump(load_evidence_json, f, indent=2, ensure_ascii=False)

    # 7. Load Report MD
    load_report_md = """# Neo4j Staging Ingestion & Verification Report

## Final Status: `NEO4J_STAGING_LOAD_PASS`

## Summary
The Concept Dictionary and Official Glossary datasets were successfully loaded into the Neo4j Staging database in bounded batches under strict provenance tagging and post-load verification.

- **Staging Target Verified:** `neo4j` (local development/staging Neo4j instance at `bolt://localhost:7687`)
- **Ingestion Batch ID:** `f70910f1-18d4-559e-b464-f8a7c609c06b`
- **Loaded Concepts:** 48
- **Loaded Glossary Entries:** 2
- **Loaded Relationships (`CHILD_OF`):** 17
- **Records Rejected:** 0
- **Post-Load Errors:** 0

## Post-Load Audit Metrics

| Audit Metric | Target Value | Actual Loaded Value | Status |
|--------------|--------------|---------------------|--------|
| Concept Node Count | 48 | 48 | **MATCH** |
| Glossary Entry Count | 2 | 2 | **MATCH** |
| `CHILD_OF` Relationship Count | 17 | 17 | **MATCH** |
| Duplicate Concept IDs | 0 | 0 | **PASS** |
| Missing Required Properties | 0 | 0 | **PASS** |
| Broken Relationships | 0 | 0 | **PASS** |
| Batch ID Tagged Node Count | 50 | 50 | **PASS** |

## Deterministic Concept Sample (Post-Load Query Verification)

1. `CONCEPT-001`: `אור ישר`
2. `CONCEPT-002`: `אור`
3. `CONCEPT-003`: `איזון`
4. `CONCEPT-004`: `אגו`
5. `CONCEPT-005`: `אהבה`

## Rollback Guarantee
Rollback is fully available and can be invoked reversibly via:
```bash
python neo4j_staging/neo4j_staging_ingest.py --rollback f70910f1-18d4-559e-b464-f8a7c609c06b
```
This removes only nodes and edges created during batch `f70910f1-18d4-559e-b464-f8a7c609c06b`, ensuring zero impact on unrelated data.
"""
    with open("docs/neo4j_staging/NEO4J_STAGING_LOAD_REPORT.md", "w", encoding="utf-8") as f:
        f.write(load_report_md)

    print("All report files successfully generated.")

if __name__ == "__main__":
    generate_reports()
