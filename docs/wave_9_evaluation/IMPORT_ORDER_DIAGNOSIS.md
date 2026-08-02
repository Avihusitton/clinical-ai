# Import Order Contamination Diagnosis Report — Wave 9.1

```text
baseline_test_restored: true
baseline_test_assertions_weakened: false
```

## Diagnosis

`tests/test_gate_cd_boundary.py` contains an assertion verifying that importing `gate_cd_boundary` does not cause `neo4j` to be imported into `sys.modules`.

When Wave 9 modules imported `retrieval.Retriever` at top-level module load time, loading any Wave 9 test module placed `neo4j` into `sys.modules` before `test_gate_cd_boundary.py` executed.

## Repair Applied

1. Restored `tests/test_gate_cd_boundary.py` to its exact pre-Wave-9 content. No assertions were weakened or removed (`baseline_test_assertions_weakened: false`).
2. Deferred `retrieval` imports inside Wave 9 function calls (`run_single_fixture`, `run_stress_harness`) so that importing Wave 9 test modules at module collection time never touches `retrieval` or `neo4j`.
3. Verified `test_gate_cd_boundary.py` passes cleanly in full pytest execution.
