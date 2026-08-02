# Repository Cleanup Strategy & Plan

**Document Status**: `INVENTORY_ONLY_NO_FILES_MOVED_OR_DELETED`  
**Files Moved**: 0  
**Files Deleted**: 0  

---

## 1. Governance & Cleanup Invariants

1. **Zero Action in Current Phase**: This task inventories candidates only. No files have been moved, renamed, or deleted (`FILES_MOVED: 0`, `FILES_DELETED: 0`).
2. **Two-Stage Quarantine Protocol**: Future cleanup actions must move candidate files to a `quarantine/` directory first before any permanent deletion is considered.
3. **Owner Sign-Off Required**: Permanent deletion of `DELETE_CANDIDATE` items requires explicit project owner approval.
4. **Unknown Item Isolation**: Unverified or `UNKNOWN` items remain untouched.

---

## 2. Specific Package Analysis: `gate_d/**` vs `models/gate_d/**`

- **`gate_d/**`**: Classified as **`ACTIVE_PRODUCTION`**. Contains the verified implementation of the Gate D Consultation Engine (`consultation_engine.py`, `safety_policy.py`, `language_policy.py`, `audit_trail.py`, `evidence_filter.py`). Active adapters (`controlled_integration/adapters/gate_d_adapter.py`) and test suites (`tests/test_gate_d_*.py`) import directly from `gate_d`.
- **`models/gate_d/**`**: Classified as **`QUARANTINE_CANDIDATE`**. Duplicate historical scaffold. No active module or test suite imports from `models.gate_d`.

---

## 3. Phased Execution Roadmap (Future Waves)

- **Phase A**: Quarantine duplicate scaffold (`models/gate_d/**`) and historical backup scripts (`ingestion_pipeline.before_*.py`).
- **Phase B**: Move root dump logs (`*_dump.txt`, `output.txt`, `temp_log.txt`) to `docs_archive/logs/`.
- **Phase C**: Request owner approval for final purge of confirmed quarantine items.
