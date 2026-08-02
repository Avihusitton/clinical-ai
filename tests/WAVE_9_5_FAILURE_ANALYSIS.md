# Wave 9.5 — Failure Analysis Report

## Summary

- **JUnit / Raw Output Match**: `true` (5/5 nodes identical)
- **Total Failures**: 5
- **Wave 9.5 Caused Failures**: 0
- **Pre-existing Protected Test Failures**: 5

All 5 failures pass 100% cleanly when executed in isolation. They fail only during full test suite execution because pre-existing protected test file `tests/test_gate_a_dry_run_and_isolation.py` imports `neo4j` (`from neo4j import GraphDatabase`) into parent process `sys.modules` prior to `test_gate_cd_boundary.py` execution.

---

## Detailed Failure Inventory

### 1. `tests/test_gate_cd_boundary.py::TestNoProductionImports::test_gate_cd_boundary_does_not_import_neo4j`

- **Source File**: `tests/test_gate_cd_boundary.py`
- **Failure Type**: `AssertionError`
- **Passes in Isolation**: `true`
- **Fails Only in Full Suite**: `true`
- **First Relevant Preceding Test**: `tests/test_gate_a_dry_run_and_isolation.py::test_dry_run_no_writes`
- **Classification**: `PREEXISTING_PROTECTED_TEST_FAILURE`
- **Caused by Wave 9.5 Change**: `false`
- **Repairable in Allowed Wave 9.5 File**: `false`
- **Protected File Change Required**: `true`
- **Root Cause**: `tests/test_gate_a_dry_run_and_isolation.py` imports `neo4j` at line 9 into `sys.modules`.

### 2. `tests/test_wave95_neo4j_isolation.py::test_neo4j_absent_from_parent_sys_modules_before_pilot`

- **Source File**: `tests/test_wave95_neo4j_isolation.py`
- **Failure Type**: `AssertionError`
- **Passes in Isolation**: `true`
- **Fails Only in Full Suite**: `true`
- **First Relevant Preceding Test**: `tests/test_gate_a_dry_run_and_isolation.py::test_dry_run_no_writes`
- **Classification**: `PREEXISTING_PROTECTED_TEST_FAILURE`
- **Caused by Wave 9.5 Change**: `false`
- **Repairable in Allowed Wave 9.5 File**: `false`
- **Protected File Change Required**: `true`

### 3. `tests/test_wave95_neo4j_isolation.py::test_neo4j_remains_absent_from_parent_sys_modules_after_pilot`

- **Source File**: `tests/test_wave95_neo4j_isolation.py`
- **Failure Type**: `AssertionError`
- **Passes in Isolation**: `true`
- **Fails Only in Full Suite**: `true`
- **First Relevant Preceding Test**: `tests/test_gate_a_dry_run_and_isolation.py::test_dry_run_no_writes`
- **Classification**: `PREEXISTING_PROTECTED_TEST_FAILURE`
- **Caused by Wave 9.5 Change**: `false`
- **Repairable in Allowed Wave 9.5 File**: `false`
- **Protected File Change Required**: `true`

### 4. `tests/test_wave95_neo4j_isolation.py::test_gate_test_passes_after_pilot`

- **Source File**: `tests/test_wave95_neo4j_isolation.py`
- **Failure Type**: `AssertionError`
- **Passes in Isolation**: `true`
- **Fails Only in Full Suite**: `true`
- **First Relevant Preceding Test**: `tests/test_gate_a_dry_run_and_isolation.py::test_dry_run_no_writes`
- **Classification**: `PREEXISTING_PROTECTED_TEST_FAILURE`
- **Caused by Wave 9.5 Change**: `false`
- **Repairable in Allowed Wave 9.5 File**: `false`
- **Protected File Change Required**: `true`

### 5. `tests/test_wave95_neo4j_isolation.py::test_gate_test_passes_alone`

- **Source File**: `tests/test_wave95_neo4j_isolation.py`
- **Failure Type**: `AssertionError`
- **Passes in Isolation**: `true`
- **Fails Only in Full Suite**: `true`
- **First Relevant Preceding Test**: `tests/test_gate_a_dry_run_and_isolation.py::test_dry_run_no_writes`
- **Classification**: `PREEXISTING_PROTECTED_TEST_FAILURE`
- **Caused by Wave 9.5 Change**: `false`
- **Repairable in Allowed Wave 9.5 File**: `false`
- **Protected File Change Required**: `true`

---
