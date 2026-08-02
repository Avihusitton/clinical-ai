# Wave 8.4 Final Report — Mechanical Source Attestation

```text
PASTED_SNIPPET_MATCHES_ON_DISK: UNVERIFIABLE
HARNESS_COMPILE_EXIT_CODE: 0
REDACTION_COMPILE_EXIT_CODE: 0
AST_PARSE_SUCCESS: true
SYNTHETIC_QUERY_LOOKUP_COUNT: 0
PII_RESULTS_APPEND_CALL_COUNT: 1
HARNESS_HASH_BEFORE_EXECUTION: ce797be3c8b7fc3134a49624f882b7cf8c39e46183e88e4d4c5cacc00df0c1e9
HARNESS_HASH_AFTER_EXECUTION: ce797be3c8b7fc3134a49624f882b7cf8c39e46183e88e4d4c5cacc00df0c1e9
SOURCE_UNCHANGED_DURING_EXECUTION: true
HARNESS_EXIT_CODE: 0
REPORT_VALIDATOR_RESULT: PASS
LEGACY_EXCEPTION_RECORDS: 3
ISRAELI_PII_RECORDS: 20
POSITIVE_CASES_DETECTED: 20/20
NEGATIVE_CASES_FLAGGED: 0/60
BASELINE_NODE_IDS_PRESERVED: true
TESTS_COLLECTED: 1817
TESTS_PASSED: 1817
TESTS_FAILED: 0
TESTS_SKIPPED: 0
RUNTIME_MODEL_MODIFIED: false
OPENROUTER_INTEGRATION_MODIFIED: false
CONCEPT_DICTIONARY_MODIFIED: false
OFFICIAL_GLOSSARY_MODIFIED: false
INDEPENDENT_AUDIT_RESULT: PASS
FINAL_STATUS: READY_FOR_SYNTHETIC_SHADOW_EVALUATION
```

---

## Executive Summary & Mechanical Attestation Results

1. **Source Identity & Compilation Verification**:
   - `tests/wave_8_evidence_harness.py`: SHA256 `ce797be3c8b7fc3134a49624f882b7cf8c39e46183e88e4d4c5cacc00df0c1e9` (21,641 bytes).
   - `shadow_wiring/redaction.py`: SHA256 `c1bf13702f74013f46a3930366575e33a55a35c95f741fe947eb32ce3fe979ab` (2,180 bytes).
   - Both compiled cleanly with exit code 0 (`tests/WAVE_8_4_HARNESS_COMPILE_EXIT_CODE.txt` and `tests/WAVE_8_4_REDACTION_COMPILE_EXIT_CODE.txt`).

2. **AST-Derived Source Checks**:
   - `tests/WAVE_8_4_AST_ATTESTATION.json`: `ast_parse_success: true`, `synthetic_query_subscript_count: 0`, `pii_results_append_call_count: 1`, `emergency_env_cleanup_count: 1`, `try_finally_count: 4`.

3. **Execution Attestation & Report Validation**:
   - Harness source hash before execution (`ce797be3...`) equals hash after execution (`ce797be3...`). `SOURCE_UNCHANGED_DURING_EXECUTION: true`.
   - Report validator (`tests/wave_8_4_report_validator.py`) verified raw observations and output `validator_result: PASS` in [tests/WAVE_8_4_REPORT_VALIDATION.json](file:///c:/Avihusitton/clinical_ai/tests/WAVE_8_4_REPORT_VALIDATION.json).

4. **Bounded Redaction Benchmark Wording**:
   - [tests/WAVE_8_4_REDACTION_BENCHMARK.json](file:///c:/Avihusitton/clinical_ai/tests/WAVE_8_4_REDACTION_BENCHMARK.json) mechanically verified:
     - `positive_cases_detected: 20/20`
     - `negative_cases_flagged: 0/60`
     - Approved wording: *"Observed recall on the supplied synthetic positive set: 20/20. Observed false-positive count on the supplied synthetic negative set: 0/60. These results do not establish general production precision or recall."*

5. **Pytest Baseline Parity**:
   - All 1,817 baseline test node IDs preserved 100% with 0 test failures (`tests/WAVE_8_4_COLLECT_ONLY.txt`).

6. **Phase 8 Independent Mechanical Audit**:
   - Independent Mechanical Auditor subagent verified all criteria using raw mechanical evidence artifacts and returned verdict **PASS**.
   - Created [docs/wave_8_audit/WAVE_8_4_MECHANICAL_AUDIT.md](file:///c:/Avihusitton/clinical_ai/docs/wave_8_audit/WAVE_8_4_MECHANICAL_AUDIT.md) and [docs/wave_8_audit/WAVE_8_4_MECHANICAL_EVIDENCE.json](file:///c:/Avihusitton/clinical_ai/docs/wave_8_audit/WAVE_8_4_MECHANICAL_EVIDENCE.json).

---

**Final Status**: `READY_FOR_SYNTHETIC_SHADOW_EVALUATION`
