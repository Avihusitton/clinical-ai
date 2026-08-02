# Dependency Evidence Report

**Document Status**: `READ_ONLY_INVENTORY`  

---

## Dependency Verification Matrix

| Candidate Path | Import References | Active Production / Test Target | Classification |
| :--- | :--- | :--- | :--- |
| `gate_d/__init__.py` | `controlled_integration/adapters/gate_d_adapter.py`, `tests/test_gate_d_*.py` | `ACTIVE_PRODUCTION` | Do NOT quarantine or delete |
| `models/gate_d/__init__.py` | None | Duplicate Scaffold | `QUARANTINE_CANDIDATE` |
| `ingestion_pipeline.before_concept_relationship_block.py` | None | Backup copy | `QUARANTINE_CANDIDATE` |
| `ingestion_pipeline.before_lexicon_guard.py` | None | Backup copy | `QUARANTINE_CANDIDATE` |
| `ingestion_pipeline.before_pdf_support.py` | None | Backup copy | `QUARANTINE_CANDIDATE` |
| `ingestion_pipeline.before_review_queue.py` | None | Backup copy | `QUARANTINE_CANDIDATE` |
| `add_review_queue_dump.txt` | None | Execution log | `GENERATED_ARTIFACT` |
| `block_dump.txt` | None | Execution log | `GENERATED_ARTIFACT` |

---

## Conclusion

No production code or test dependencies exist for items classified as `QUARANTINE_CANDIDATE` or `GENERATED_ARTIFACT`. No files were moved or deleted during this task (`FILES_MOVED: 0`, `FILES_DELETED: 0`).
