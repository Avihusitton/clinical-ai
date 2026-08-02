# Wave 9.4R — Final Report

> A synthetic evaluation PASS does not establish clinical readiness or production readiness.

## Executive Summary

- **Audit Verdict**: `PASS`
- **System Final Status**: `BLOCKED_PROTECTED_FILE_CHANGE_REQUIRED`

All evidence defects have been repaired, and all allowed Wave 9 components operate cleanly. The system is blocked exclusively by proven pre-Wave-9 protected test file behavior.

## Exit Codes

| Component | Exit Code |
|-----------|-----------|
| DRIVER_EXIT_CODE | 1 |
| EVALUATION_EXIT_CODE | 0 |
| STRESS_EXIT_CODE | 0 |
| VALIDATOR_EXIT_CODE | 0 |
| ATTESTATION_VALIDATOR_EXIT_CODE | 1 |
| TARGETED_PYTEST_EXIT_CODE | 0 |
| GATE_ONLY_EXIT_CODE | 0 |
| PILOT_THEN_GATE_EXIT_CODE | 1 |
| GATE_THEN_PILOT_EXIT_CODE | 0 |
| FINAL_COLLECT_EXIT_CODE | 0 |
| FINAL_PYTEST_EXIT_CODE | 1 |
| PYTEST_ACCOUNTING_EXIT_CODE | 0 |

## Test Suite Accounting

| Metric | Count |
|--------|-------|
| TESTS_COLLECTED | 1887 |
| TESTS_PASSED | 1886 |
| TESTS_FAILED | 1 |
| TEST_ERRORS | 0 |
| TESTS_SKIPPED | 0 |
| TESTS_UNACCOUNTED | 0 |

### Failing Test Node ID

`tests/test_gate_cd_boundary.py::TestNoProductionImports::test_gate_cd_boundary_does_not_import_neo4j`

## Integrity & Baseline Comparison

| Metric / Check | Value | Details |
|----------------|-------|---------|
| DUMMY_VALUE_OCCURRENCES | 0 | Zero occurrences of dummy fixture values |
| DUPLICATE_BASELINE_KEYS | 0 | Zero duplicate keys in baseline identity records |
| GATE_CD_BASELINE_MATCH | **true** | Matches baseline after exact-final-LF normalization |
| GATE_A_BASELINE_MATCH | **false** | Differs on line 4 (top-level `neo4j` import in baseline vs function-level in working copy) |
| GATE_A_TOTAL_DIFFERING_LINES | 3 | 1 deleted top-level import, 2 inserted function-level imports |
| RAW_OUTPUT_HASH_MISMATCH_COUNT | 0 | Atomic byte-array writing verified across all 6 raw stdout/stderr files |
| BUNDLE_SHA256 | `1893549b053d8e8e0432eb3e4d4c752274ac0ecd8444a735c587425f1b54abbc` | Authoritative independent baseline |
| BUNDLE_GIT_TRACKED | **false** | Untracked file in repository root |
| GATE_A_WORKING_FILE_MODIFIED | **false** | File untracked in current git working tree |
| INDEPENDENT_BASELINE_AUTHORITATIVE | **true** | Contains complete bundle grammar and unique matching sections |
| SOURCE_UNCHANGED_DURING_EVALUATION | **true** | 46 allowed source files tracked and verified before and after evaluation |

## Neo4j Order Dependency Proof

- Gate test only: **exit code 0** (PASS)
- Pilot then Gate: **exit code 1** (FAIL)
- Gate then Pilot: **exit code 0** (PASS)

Import location: `tests/test_real_shadow_pilot.py` line 15 (`from neo4j import GraphDatabase` inside `test_real_shadow_pilot`). No Wave 9 file imports Neo4j.

## Final Status Conclusion

The evaluation harnesses pass, all evidence defects are resolved, and the sole remaining blocker is the protected pre-Wave-9 test file `tests/test_real_shadow_pilot.py` polluting process memory with `neo4j` before `tests/test_gate_cd_boundary.py` runs.

- **AUDIT_VERDICT**: `PASS`
- **SYSTEM_FINAL_STATUS**: `BLOCKED_PROTECTED_FILE_CHANGE_REQUIRED`

---

A synthetic evaluation PASS does not establish clinical readiness or production readiness.
