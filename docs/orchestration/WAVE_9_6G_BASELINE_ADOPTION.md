# Wave 9.6G — Forward Canonical Baseline Adoption

## Governance Statement

The current Wave 9.6 implementation is adopted as the forward canonical baseline.

No authoritative pre-Wave-9.6 source was available.

Historical behavior equivalence was not established.

The adoption is based on current mechanical verification, process isolation tests, and a full suite result of 1904 passed, 0 failed and 0 errors.

This adoption does not establish clinical readiness or production readiness.

Live clinical traffic and live patient data remain unauthorized.

---

## Baseline Inventory & Hashes

The forward canonical baseline comprises the following verified frozen components:

- `tests/test_gate_a_dry_run_and_isolation.py` (988 bytes, SHA-256: `1ab7de7bda639ab5f12efba853ca949a991cc7d9631fd688e86af883116be467`)
- `evaluation/wave96/gate_a_driver_runner.py` (9463 bytes, SHA-256: `adfebb6a3c79de3c8bced2e74b549f4da65f0ae98ef4e88d656b2dde39b4b66f`)
- `tests/test_wave96_gate_a_isolation.py` (7075 bytes, SHA-256: `26312416ee9ec2c9ce606504224db90d12b74fe953ef12e18a12a7308132d5b8`)
- `tests/test_gate_cd_boundary.py` (20914 bytes, SHA-256: `0510f87714c630505a6de93eeac5de6c8a61915dc379a0b0977d02de36c2e936`)

## Canonical Verification Context

- `baseline_effective_from_wave`: `WAVE_9_6G`
- `baseline_type`: `FORWARD_CANONICAL_BASELINE`
- `historical_equivalence_proven`: `false`
