# Wave 3 Independent Audit

## Gate C: Novelty Discovery Engine
- **Novelty remains discovery-only**: Verified in `GATE_C_NOVELTY_CONTRACT.md` (`DISCOVERY_ONLY`, `PENDING_HUMAN_REVIEW`).
- **Human review is mandatory**: Verified. Unknown thresholds fail closed, triggering human review.
- **No automatic promotion**: Verified. Absolute prohibition on automatic promotion.
- **Known knowledge is separated from novelty**: Verified via `KnownKnowledgeCheck` and graph write restrictions.
- **Duplicates and contradictions are handled**: Verified via `duplicate_risk` and `contradiction_risk`.
- **Provenance is mandatory**: Verified via `provenance_quality`.
- **Unknown thresholds fail closed**: Verified.
- **No graph writes are allowed**: Verified. Absolute prohibition on permanent writes to the graph.
- **At least 60 Gate C fixtures exist**: Verified in `tests/fixtures/gate_c/novelty_cases.jsonl` (60 fixtures).

## Gate D: Consultation System
- **Human clinical authority is explicit**: Verified in `GATE_D_CONSULTATION_CONTRACT.md`.
- **Diagnosis and treatment decisions are prohibited**: Verified in prohibited system functions.
- **No live patient data is allowed**: Verified. Only synthetic or anonymized cases permitted.
- **PII is rejected**: Verified.
- **Evidence and uncertainty are displayed**: Verified.
- **Direct patient-facing operation is prohibited**: Verified.
- **Crisis automation is prohibited**: Verified. Blocked scenarios include crisis automation.
- **Therapist override and audit trail are mandatory**: Verified in `GATE_D_SAFETY_CONTRACT.md`.
- **At least 60 Gate D fixtures exist**: Verified in `tests/fixtures/gate_d/consultation_cases.jsonl` (60 fixtures).

## Shared Pilot Rules
- **Gate C candidates cannot become consultation facts without approval**: Verified.
- **Gate D does not consume unreviewed novelty as evidence**: Verified.
- **Legacy fallback and rollback are required**: Verified.
- **The finish line remains internal pilot, not production**: Verified.
- **No protected files changed**: Verified.

**Result**: PASS
