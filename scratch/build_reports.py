import json

diff_text = """
```diff
@@ -51,7 +51,6 @@
 MATCH path = (start:Concept {canonical_name: $start})
              -[:{rel_types}*1..{depth}]->
              (end:Concept)
-WHERE ALL(n IN nodes(path) WHERE NOT "Exercise" IN labels(n))
 RETURN
     [n IN nodes(path) | n.canonical_name] AS concept_chain,
     [r IN relationships(path) | {{
@@ -143,7 +144,7 @@ class Retriever:
             f"=== הקשר ראייתי (ציטוטים + metadata, לשיפוט רלוונטיות בלבד) ===\\n{evidence_block}\\n\\n"
             f"=== תרגילים מקושרים (עיטור טרמינלי, עומק 1) ===\\n{exercises_block}"
         )
-        return self.llm._call(system, user, mock_response="[מצב מוק - אין תשובה אמיתית]")
+        return self.llm._call(system, user, mock_response="MOCK_ANSWER")
```
"""

content = f"""# Gate A Checkpoint

## 1. `retrieval.py` Diff and Disposition

The following unauthorized modifications were made during Gate A, mixing a behavior change with an encoding repair:

{diff_text}

**Disposition**:
* The **production reasoning behavior change** (`WHERE ALL(n IN nodes...`) has been **reverted** to the legacy baseline. It did not exist before the Gate A commit.
* The **test/mock encoding correction** (`mock_response="MOCK_ANSWER"`) was kept, as it only repairs test-suite execution without affecting production logic.
* **Future Gate Recommendation**: The Exercise-bridge issue is a legitimate defect in legacy behavior and should be fixed in a future controlled retrieval-refactoring gate by applying the `WHERE ALL(...)` constraint.

---

## 2. Complete Test Suite Output

```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\\Avihusitton\\clinical_ai
plugins: anyio-4.13.0
collecting ... collected 16 items

tests/test_official_glossary_store.py::test_store_loads_data PASSED
tests/test_official_glossary_store.py::test_hash_stability PASSED
tests/test_official_glossary_store.py::test_schema_validation PASSED
tests/test_official_glossary_loader.py::test_loader_dry_run PASSED
tests/test_glossary_alias_index.py::test_trie_alias_matcher_longest_match PASSED
tests/test_glossary_alias_index.py::test_trie_alias_matcher_normalization PASSED
tests/test_glossary_alias_index_boundaries.py::test_trie_boundaries PASSED
tests/test_retrieval_baseline.py::test_baseline_retrieval PASSED
tests/test_retrieval_baseline.py::test_retrieval_characterization PASSED
tests/test_retriever_behavior.py::test_retriever_outcomes PASSED
tests/test_gate_a_dry_run_and_isolation.py::test_dry_run_no_writes PASSED
tests/test_gate_a_dry_run_and_isolation.py::test_shadow_isolation PASSED
tests/test_eval_dataset.py::test_evaluation_dataset_contract PASSED
tests/test_gate_a_metrics.py::test_gate_a_metrics PASSED
tests/test_ast_audit.py::test_no_duplicate_functions_or_classes PASSED
tests/test_migration.py::test_migration_preserves_unrelated_fields PASSED

============================= 16 passed in 1.43s ==============================
```

---

## 3. Dataset Validation Output

```text
total_records: 180
duplicate_case_ids: 0
duplicate_normalized_records: 0
invalid_spans: 0
missing_cards: 0
negative_cases_with_positive_spans: 0
category_counts:
  LONGEST_MATCH: 25
  WORD_BOUNDARY: 25
  NIQQUD: 20
  PUNCTUATION: 20
  MIXED_RTL_LTR: 20
  OVERLAPPING_TERMS: 20
  UNSAFE_SHORT_ALIAS: 20
  NEGATIVE_FALSE_POSITIVE: 20
  ALIAS_COLLISION: 10
```

---

## 4. Overall and Per-Category Metrics

```json
{json.dumps(json.load(open("tests/GATE_A_METRICS.json")), indent=2)}
```

---

## 5. Dry-Run Query Audit

```json
{json.dumps(json.load(open("tests/DRY_RUN_REPORT.json")), indent=2)}
```

---

## 6. Shadow Isolation Numbers

```json
{json.dumps(json.load(open("tests/ISOLATION_REPORT.json")), indent=2)}
```
*Note: The behavioral tests created and cleaned up a fixture graph in the production label space because the legacy retrieval engine hardcodes `Concept` labels.*

---

## 7. AST Audit

```text
activate_lexicons.py | OK | [] | [] | []
add_lexicon_guard.py | OK | [] | [] | []
add_missing_synonyms.py | OK | [] | [] | []
add_pdf_support.py | OK | [] | [] | []
add_relationship_guard.py | OK | [] | [] | []
add_review_queue.py | OK | [] | [] | []
auto_ingest_loop.py | OK | [] | [] | []
backfill_relationships.py | OK | [] | [] | []
benchmark_trie.py | OK | [] | [] | []
block_concept_relationships.py | OK | [] | [] | []
build_glossary.py | OK | [] | [] | []
check_neo4j_ready.py | OK | [] | [] | []
cleanup_shadow.py | OK | [] | [] | []
config.py | OK | [] | [] | []
curate_glossary.py | OK | [] | [] | []
diagnose_docx.py | OK | [] | [] | []
document_types_inspector.py | OK | [] | [] | []
file_manager.py | OK | [] | [] | []
glossary_alias_index.py | OK | [] | [] | []
ingestion_pipeline.before_concept_relationship_block.py | OK | [] | [] | []
ingestion_pipeline.before_lexicon_guard.py | OK | [] | [] | []
ingestion_pipeline.before_pdf_support.py | OK | [] | [] | []
ingestion_pipeline.before_review_queue.py | OK | [] | [] | []
ingestion_pipeline.py | OK | [] | [] | []
llm_client.py | OK | [] | [] | []
load_approved_relationships.py | OK | [] | [] | []
master_dashboard.py | OK | [] | [] | []
neo4j_after_load.py | OK | [] | [] | []
neo4j_baseline.py | OK | [] | [] | []
neo4j_before_load.py | OK | [] | [] | []
neo4j_diagnose_duplicates.py | OK | [] | [] | []
neo4j_full_status.py | OK | [] | [] | []
official_glossary_loader.py | OK | [] | [] | []
official_glossary_store.py | OK | [] | [] | []
patch.py | OK | [] | [] | []
prepare_preflight.py | OK | [] | [] | []
refine_drafts.py | OK | [] | [] | []
reset_environment.py | OK | [] | [] | []
restore_draft.py | OK | [] | [] | []
retrieval.py | OK | [] | [] | []
review_app.py | OK | [] | [] | []
review_glossary.py | OK | [] | [] | []
review_glossary_app.py | OK | [] | [] | []
run_all.py | OK | [] | [] | []
run_full_pipeline.py | OK | [] | [] | []
setup.py | OK | [] | [] | []
test_candidate_matching.py | OK | [] | [] | []
test_live_llm.py | OK | [] | [] | []
track_progress.py | OK | [] | [] | []
wait_for_files.py | OK | [] | [] | []
tests/benchmark_evaluation.py | OK | [] | [] | []
tests/test_ast_audit.py | OK | [] | [] | []
tests/test_eval_dataset.py | OK | [] | [] | []
tests/test_gate_a_dry_run_and_isolation.py | OK | [] | [] | []
tests/test_gate_a_metrics.py | OK | [] | [] | []
tests/test_glossary_alias_index.py | OK | [] | [] | []
tests/test_glossary_alias_index_boundaries.py | OK | [] | [] | []
tests/test_migration.py | OK | [] | [] | []
tests/test_official_glossary_loader.py | OK | [] | [] | []
tests/test_official_glossary_store.py | OK | [] | [] | []
tests/test_retrieval_baseline.py | OK | [] | [] | []
tests/test_retriever_behavior.py | OK | [] | [] | []
```

---

## 8. Migration-Test Proof

```text
def test_migration_preserves_unrelated_fields():
    original = {{
        "card_id": "T001",
        "entry_name": "T001 is a great concept",
        "updated_at": "2023-01-01T00:00:00Z",
        "parent_terms": ["T002", "T003"],
        "card_hash": "T001HASH"
    }}
    
    migrated = migrate_identifiers_in_record(original)
    
    assert migrated["card_id"] == "Z901"
    assert migrated["entry_name"] == "T001 is a great concept", "Prose must not be modified"
    assert migrated["updated_at"] == "2023-01-01T00:00:00Z", "Timestamps must not be modified"
    assert migrated["parent_terms"] == ["Z902", "Z903"], "List identifiers must be modified"
    assert migrated["card_hash"] == "T001HASH", "Hashes must not be modified"
```
*(Test execution: `tests/test_migration.py::test_migration_preserves_unrelated_fields PASSED`)*

---

## 9. Entry-Type Provisional Metadata

From `data/official_glossary/entry_types.json`:
```json
{json.dumps(json.load(open("data/official_glossary/entry_types.json", encoding="utf-8")), indent=2, ensure_ascii=False)}
```

---

## 10. Known Limitations

- `retrieval.py` allows `Exercise` nodes to act as intermediate nodes. This was confirmed to be legacy behavior and reverted to baseline for characterization purposes.
- Tests that verify current legacy retrieval behavior in Neo4j do not use Shadow Isolation labels, meaning they instantiate and drop exact production nodes during test execution.

---

## Status
READY_FOR_GATE_B
"""

with open("GATE_A_CHECKPOINT.md", "w", encoding="utf-8") as f:
    f.write(content)

with open("GATE_A_FINAL_FILE_AUDIT.md", "w", encoding="utf-8") as f:
    f.write("# Gate A Final File Audit\\n\\nAll python and test files have been verified to contain no duplicate definitions (functions, classes, tests) via AST parsing. See AST Audit table in GATE_A_CHECKPOINT.md.")
