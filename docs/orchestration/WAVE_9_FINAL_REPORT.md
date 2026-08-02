# Wave 9 Final Report — Synthetic Shadow Evaluation and Benchmark

```text
CURRENT_BRANCH: feat/wave9-synthetic-shadow-evaluation
FIXTURES_LOADED: 140
FIXTURES_ACCOUNTED_FOR: 140
LEGACY_EXACT_MATCHES: 140
USER_VISIBLE_SHADOW_OUTPUTS: 0
ISRAELI_PII_CASES_EVALUATED: 20
ISRAELI_PII_CASES_QUEUED: 0
NEGATIVE_REDACTION_CASES_EVALUATED: 60
NEGATIVE_REDACTION_CASES_FLAGGED: 0
DETERMINISTIC_RUN_COUNT: 3
DETERMINISTIC_FIXTURE_OUTCOMES: 140/140
QUEUE_PROFILES_COMPLETED: 9
REQUEST_THREAD_WAITS: 0
REQUEST_THREAD_RETRIES: 0
RAW_QUERY_LEAKS: 0
DIFFERENCE_CLASSES_OBSERVED: ["AGREEMENT", "CONTROLLED_DIFFERENCE", "EMERGENCY_DISABLED", "PII_REJECTED", "SHADOW_DISABLED"]
DIFFERENCE_CLASSES_UNREACHABLE: ["FALLBACK_TRIGGERED", "LEGACY_ONLY_EVIDENCE", "RANKING_DIFFERENCE", "SAFETY_BLOCK_DIFFERENCE", "SHADOW_ERROR", "SHADOW_ONLY_REVIEWED_EVIDENCE", "SHADOW_TIMEOUT", "UNCERTAINTY_DIFFERENCE"]
LOCAL_OVERHEAD_P50: 55.8 µs
LOCAL_OVERHEAD_P95: 74.6 µs
LOCAL_OVERHEAD_P99: 182.4 µs
CONTROLLED_INTEGRATION_SYNTHETIC_LIMITATIONS: Synthetic adapter output is plumbing evidence only. It is not evidence of real clinical retrieval or knowledge quality.
BASELINE_NODE_IDS_PRESERVED: true
TESTS_COLLECTED: 1844
TESTS_PASSED: 1844
TESTS_FAILED: 0
TESTS_SKIPPED: 0
PRODUCTION_FILES_MODIFIED: 0
RUNTIME_MODEL_MODIFIED: false
OPENROUTER_INTEGRATION_MODIFIED: false
CONCEPT_DICTIONARY_MODIFIED: false
OFFICIAL_GLOSSARY_MODIFIED: false
NEO4J_CALLS_EXECUTED: 0
NETWORK_CALLS_EXECUTED: 0
LLM_CALLS_EXECUTED: 0
LIVE_PATIENT_DATA_USED: false
INDEPENDENT_AUDIT_RESULT: PASS
FINAL_STATUS: SYNTHETIC_SHADOW_EVALUATION_PASS
RECOMMENDED_NEXT_STEP: Separate Runtime Model Alignment Compatibility Task
```

> [!IMPORTANT]
> A synthetic evaluation PASS does not establish clinical readiness or production readiness.

---

## Executive Summary & Wave 9 Evaluation Accomplishments

1. **Synthetic Shadow Plumbing & Legacy Invariance**:
   - All 140 synthetic fixtures in [tests/fixtures/shadow_wiring/shadow_cases.jsonl](file:///c:/Avihusitton/clinical_ai/tests/fixtures/shadow_wiring/shadow_cases.jsonl) were evaluated across 7 domains (`shadow_disabled`, `agreement`, `controlled_difference`, `failure_and_timeout`, `security_and_redaction`, `rollback_and_emergency`, `israeli_pii`).
   - Legacy exact matches: 140/140 (`LEGACY_EXACT_MATCHES: 140`).
   - User-visible Shadow outputs: 0 (`USER_VISIBLE_SHADOW_OUTPUTS: 0`).
   - Raw query leaks: 0 (`RAW_QUERY_LEAKS: 0`).

2. **Mode Behavior & Safety Controls**:
   - `LEGACY_ONLY`, `SHADOW_COMPARE`, `EMERGENCY_DISABLED`, and `UNKNOWN_MODE` evaluated.
   - Unknown operating modes fail closed immediately to `LEGACY_ONLY`.
   - Emergency disable halts background worker creation and rejects task queueing.

3. **Privacy Controls & Israeli PII Rejection**:
   - 20 Israeli PII synthetic cases evaluated: 20 detected, 0 queued (`ISRAELI_PII_CASES_QUEUED: 0`).
   - 60 negative redaction cases evaluated: 0 flagged (`NEGATIVE_REDACTION_CASES_FLAGGED: 0`).
   - Recorded approved disclaimer: *"Observed performance applies only to the supplied synthetic fixture sets. These results do not establish general production precision or recall."*

4. **100% Deterministic Execution**:
   - Executed 3 complete runs over all 140 fixtures (`DETERMINISTIC_RUN_COUNT: 3`).
   - Deterministic fixture outcomes: 140/140 (`DETERMINISTIC_FIXTURE_OUTCOMES: 140/140`).

5. **Queue Stress & Local Request-Path Overhead Benchmarks**:
   - Completed 9 stress profiles across queue capacities `q=1`, `q=4`, `q=16` and 3 worker profiles (`fast`, `blocked`, `exception`).
   - Safety Invariants: `REQUEST_THREAD_WAITS: 0`, `REQUEST_THREAD_RETRIES: 0`, `worker_survival: true`.
   - Measured 1,000 iterations per mode for local request-path overhead:
     - `LEGACY_ONLY` baseline: median 46.3 µs, p95 69.7 µs, p99 172.6 µs.
     - `SHADOW_COMPARE` (fast runner): median 55.8 µs, p95 74.6 µs, p99 182.4 µs.
     - `SHADOW_COMPARE` (blocked worker): median 56.5 µs, p95 75.9 µs, p99 187.1 µs.
     - `SHADOW_COMPARE` (full queue): median 57.0 µs, p95 74.2 µs, p99 194.1 µs.

6. **Synthetic Adapter Disclosures**:
   - Created [docs/wave_9_evaluation/SYNTHETIC_ADAPTER_REALITY_CHECK.md](file:///c:/Avihusitton/clinical_ai/docs/wave_9_evaluation/SYNTHETIC_ADAPTER_REALITY_CHECK.md) and [docs/wave_9_evaluation/SYNTHETIC_ADAPTER_REALITY_CHECK.json](file:///c:/Avihusitton/clinical_ai/docs/wave_9_evaluation/SYNTHETIC_ADAPTER_REALITY_CHECK.json).
   - Explicitly states: *"Synthetic adapter output is plumbing evidence only. It is not evidence of real clinical retrieval or knowledge quality."*

7. **Mechanical Validation & Pytest Parity**:
   - [evaluation/wave9/validator.py](file:///c:/Avihusitton/clinical_ai/evaluation/wave9/validator.py) recalculates all reported metrics directly from raw JSON/JSONL records.
   - 13 validator mutation tests in [tests/test_wave9_evaluation_validator.py](file:///c:/Avihusitton/clinical_ai/tests/test_wave9_evaluation_validator.py) passed (`validator_result: PASS`).
   - Full pytest suite: 1,844 passed, 0 failed (1,831 baseline node IDs preserved + 13 new Wave 9 tests = 1,844 total).

8. **Independent Wave 9 Audit**:
   - Independent Evaluation Auditor subagent verified all 14 criteria using raw mechanical evidence artifacts and returned verdict **PASS**.
   - Created [docs/wave_9_audit/WAVE_9_INDEPENDENT_AUDIT.md](file:///c:/Avihusitton/clinical_ai/docs/wave_9_audit/WAVE_9_INDEPENDENT_AUDIT.md) and [docs/wave_9_audit/WAVE_9_EVIDENCE_MATRIX.json](file:///c:/Avihusitton/clinical_ai/docs/wave_9_audit/WAVE_9_EVIDENCE_MATRIX.json).

---

**Final Status**: `SYNTHETIC_SHADOW_EVALUATION_PASS`  
**Recommended Next Step**: `Separate Runtime Model Alignment Compatibility Task`
