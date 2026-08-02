# Roadmap to Internal Pilot

## Phase 1: Foundation (Gates A & B)
- Establish infrastructure, security boundaries, and RBAC.
- Implement data minimization and PII redaction pipelines.

## Phase 2: Intelligence (Gate C)
- Build and validate the clinical GraphRAG pipeline.
- Audit evidence provenance and accuracy.

## Phase 3: Safety and Governance (Gate D)
- Define safety contracts and test matrices (Current Phase).
- Implement feature flags, audit logging, and fallback mechanisms.
- Execute the 60-case synthetic evaluation suite.

## Phase 4: Pre-flight Checks
- Complete clinical reviewer sign-off.
- Verify `INTERNAL_CLINICAL_PILOT_READY` criteria.
- Conduct mock incident response and rollback drills.

## Phase 5: Pilot Launch
- Enable feature flag for authorized internal therapists.
- Commence weekly monitoring and feedback cycles.
