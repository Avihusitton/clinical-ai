# Internal Pilot Acceptance Criteria

## Overview
The internal pilot can only commence when the condition `INTERNAL_CLINICAL_PILOT_READY` is met.

## Criteria for INTERNAL_CLINICAL_PILOT_READY
1. **Gate A Closed**: All foundational safety and compliance checks passed.
2. **Gate B Closed**: System architecture and data flow security verified.
3. **Gate C Audited**: Knowledge base and graph RAG accuracy audited and approved.
4. **Gate D Audited**: Safety, governance, and evaluation design audited and signed off.
5. **No Live Patient Data**: Strict mechanisms in place ensuring zero live patient data enters the system.
6. **No Autonomous Decisions**: The system cannot take any autonomous action regarding patient care.
7. **Therapist-Only Access**: Access is restricted entirely to authorized internal clinical staff via RBAC.
8. **Full Evidence/Uncertainty**: The UI and API explicitly display evidence provenance and uncertainty metrics.
9. **Feature Flag**: The entire pilot capability is wrapped in a master feature flag.
10. **Legacy Fallback**: A functional fallback exists if the AI system fails or is disabled.
11. **Rollback**: Documented and tested rollback procedures are in place.
12. **Audit Trail**: Comprehensive, immutable audit logging is active for all interactions.
13. **Safety Evaluation Passed**: The system passes 100% of the 60 synthetic cases defined in the Gate D test matrix.
14. **Clinical Reviewer Sign-off**: Formal approval from the clinical review board.
15. **Documented Known Limitations**: A comprehensive list of known limitations is published and accessible to all pilot users.
