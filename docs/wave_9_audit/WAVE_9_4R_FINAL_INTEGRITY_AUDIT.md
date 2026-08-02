# Wave 9.4R — Final Integrity Audit

## Audit Overview

- **Audit Verdict**: `PASS`
- **System Final Status**: `BLOCKED_PROTECTED_FILE_CHANGE_REQUIRED`

This independent audit inspects the frozen source state (`tests/WAVE_9_4R_FINAL_SOURCE_STATE.json`) and the complete evidence chain generated during Wave 9.4R closure execution.

## Evidence Verification Summary

| Evidence Item | Requirement | Actual Value | Verdict |
|---------------|-------------|--------------|---------|
| Dummy Values (`dummy1`, `dummy2`) | 0 occurrences | 0 | ✅ PASS |
| Duplicate Baseline Keys | 0 duplicate keys | 0 | ✅ PASS |
| Clean Fixture Live Evidence Copying | `false` | `false` | ✅ PASS |
| Unreachable Assertions | `false` | `false` | ✅ PASS |
| Targeted Pytest Exit Code | `0` | `0` | ✅ PASS |
| Gate CD Baseline Match | `true` | `true` | ✅ PASS |
| Gate A Baseline Match | `false` | `false` | ✅ Substantive Blocker |
| Gate A Differing Lines | Substantive diff | 3 lines | ✅ Verified |
| Raw Output Hash Mismatches | 0 mismatches | 0 | ✅ PASS |
| Source Inventory Stability | Unchanged (46 files) | 46 files unchanged | ✅ PASS |
| Neo4j Order Dependency Proof | `0`, `1`, `0` | `0`, `1`, `0` | ✅ Mechanically Proven |

## Provenance Analysis

- **Baseline Source**: `PROJECT_CODE_BUNDLE.txt` (SHA-256: `1893549b053d8e8e0432eb3e4d4c752274ac0ecd8444a735c587425f1b54abbc`)
- **Bundle Tracking**: Untracked (`??`) in working directory, unique matching sections for both Gate CD (lines 75850–76370) and Gate A (lines 72702–72891).
- **Gate CD Baseline**: Matches working file on disk after exact-final-LF normalization (`baseline_normalized_sha256 == working_normalized_sha256`).
- **Gate A Baseline**: Baseline contains top-level `from neo4j import GraphDatabase` at line 4, whereas working file has moved `neo4j` imports inside function bodies (`test_dry_run_no_writes` and `test_shadow_isolation`). This is a substantive pre-Wave-9 difference present in the authoritative baseline bundle.

## Subprocess Execution Results

| Subprocess | Exit Code | Result |
|------------|-----------|--------|
| Evaluation Harness | 0 | PASS |
| Stress Harness | 0 | PASS |
| Validator | 0 | PASS |
| Attestation Validator | 1 | FAIL (`baseline_test_identity_mismatched`) |

## Test Suite Accounting

- **Collected**: 1887
- **Passed**: 1886
- **Failed**: 1 (`tests/test_gate_cd_boundary.py::TestNoProductionImports::test_gate_cd_boundary_does_not_import_neo4j`)
- **Errors**: 0
- **Skipped**: 0

## Protected-File Blocker Determination

The sole remaining test failure in the entire 1,887-test suite is `test_gate_cd_boundary_does_not_import_neo4j`.

Mechanically proven order dependency:
1. Gate test only: Exit code **0** (PASSED)
2. Pilot then Gate (`test_real_shadow_pilot` → `test_gate_cd_boundary`): Exit code **1** (FAILED)
3. Gate then Pilot (`test_gate_cd_boundary` → `test_real_shadow_pilot`): Exit code **0** (PASSED)

Import location: `tests/test_real_shadow_pilot.py` line 15 (`from neo4j import GraphDatabase` inside `test_real_shadow_pilot`).

Because repairing this failure or reconciling Gate A baseline identity requires modifying protected pre-Wave-9 test files (`tests/test_real_shadow_pilot.py` or `tests/test_gate_a_dry_run_and_isolation.py`), and no allowed Wave 9 file imports Neo4j, the system status is conclusively **`BLOCKED_PROTECTED_FILE_CHANGE_REQUIRED`**.

---

- **AUDIT_VERDICT**: `PASS`
- **SYSTEM_FINAL_STATUS**: `BLOCKED_PROTECTED_FILE_CHANGE_REQUIRED`
