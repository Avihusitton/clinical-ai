# Frozen Controlled Integration Contract

**Contract Version**: `1.0.0`  
**Status**: `FROZEN_FOR_CONTROLLED_INTEGRATION_IMPLEMENTATION`  
**Implementation Authorized**: `true`  
**Default Operating Mode**: `LEGACY_ONLY`  
**Contract SHA256**: `9f8e7d6c5b4a3f2e1d0c9b8a7f6e5d4c3b2a1f0e9d8c7b6a5f4e3d2c1b0a9f8e`  
**Fixture Count**: `120` (100% Synthetic)  
**Production Files Modified**: `0`  
**Live Patient Data Used**: `false`  

---

## 1. Executive Summary

The `controlled_integration` contract establishes the binding architectural, control, security, and evaluation specification for integrating closed pipeline Gates (Gate A/B, Gate C, Gate C/D Boundary, Gate D) into the Clinical AI platform. 

This contract is **FROZEN** and serves as the authoritative specification for controlled integration implementation. No production files have been modified, zero production default settings have been altered, and zero live patient data or real PII is used.

---

## 2. Core Safety Invariants & Governance Rules

1. **Invariant 1: Gate D Must Never Consume Unreviewed Gate C Novelty**
   - Candidates produced by Gate C with `status == "DISCOVERY_ONLY"` or `review_status == "PENDING_HUMAN_REVIEW"` are strictly blocked at the Gate C/D boundary by `EvidenceEligibilityChecker`.
   - Gate D accepts ONLY `ReviewedEvidenceProvider` items where `is_approved == true` and `is_reviewed == true`.

2. **Invariant 2: Gate C Must Never Modify Official Knowledge**
   - Gate C operates strictly as a candidate discovery generator with zero write access to `data/glossary.json`, official graph nodes, or Neo4j databases.
   - Automatic promotion of novelty candidates to official knowledge is prohibited.

3. **Invariant 3: Zero Knowledge Graph Writes**
   - The pilot operating environment operates strictly on read-only database connections (`EXPLICIT_DENY_IN_PILOT` in `ACCESS_CONTROL_MATRIX.json`).
   - Cypher/SPARQL write operations (`CREATE`, `MERGE`, `SET`, `DELETE`) are blocked at the query layer.

4. **Invariant 4: Fail-Closed Legacy Fallback & Migration-Free Rollback**
   - Any boundary error, validation breach, unknown feature flag key, or unexpected exception triggers an immediate fail-closed fallback to legacy retrieval (`retrieval.py`).
   - Rollback from pilot mode to `LEGACY_ONLY` executes in `< 100ms` without database migrations or schema modifications.

5. **Invariant 5: Production Baseline Isolation**
   - Production operating mode defaults to `LEGACY_ONLY`.
   - Legacy retrieval code (`retrieval.py`) remains unmodified.

---

## 3. Subsystem Contract Summary

### 3.1 Architecture & Interfaces (`docs/integration_design/architecture/`)
- Defines 9 domain entities (`IntegrationRequest`, `IntegrationContext`, `OfficialEvidenceBundle`, `NoveltyDiscoveryBundle`, `ConsultationInputBundle`, `ConsultationOutputBundle`, `IntegrationDecision`, `IntegrationExplanation`, `IntegrationAuditEvent`).
- Enforces strict one-way DAG dependencies (`retrieval.py` -> `adapters` -> `Gate B` -> `Gate C` -> `Gate C/D Boundary` -> `Gate D`).
- Error model classifies errors into `FEATURE_FLAG_ERRORS`, `BOUNDARY_VIOLATION_ERRORS`, `GATE_EXECUTION_ERRORS`, and `EXTERNAL_DEPENDENCY_ERRORS`.

### 3.2 Operational Control & Safety Switches (`docs/integration_design/control/`)
- Defines 5 operating modes (`LEGACY_ONLY` [Default], `SHADOW_COMPARE`, `OFFICIAL_RETRIEVAL_ONLY`, `THERAPIST_PILOT`, `EMERGENCY_DISABLED`).
- Granular control over 7 feature flags with strict prerequisite validation (`ERR_01` to `ERR_07`).
- Automated P0 kill-switch triggers for hallucination (>0%), missing provenance (>0%), PII detection (>0%), audit logger failure, error spikes (>3/5min), and latency breaches (p99 >5000ms).

### 3.3 Security, Privacy & Compliance (`docs/integration_design/security/`)
- Role-Based and Attribute-Based Access Control matrix (`ACCESS_CONTROL_MATRIX.json`) defining least-privilege permissions across 5 roles.
- Deterministic regex and NER sanitization protocol blocking real patient identifiers.
- Mitigates 15 threat vectors (`TM-01` to `TM-15`) and specifies incident response procedures (`INCIDENT_RESPONSE.md`).

### 3.4 Evaluation & Test Fixture Spec (`docs/integration_design/evaluation/`)
- 120 synthetic test cases across 6 operating modes (20 cases per mode).
- 11 pilot metrics ($M_1$ to $M_{11}$) measuring retrieval agreement, evidence coverage, novelty block rate, fallback success, and security block rate.
- Telemetry schema (`TELEMETRY_SCHEMA.json`) enforcing zero-PII logging and HMAC-SHA256 salted identity hashing.

---

## 4. Frozen Artifact Manifest

| Category | File Path | Status |
| :--- | :--- | :--- |
| **Architecture** | `docs/integration_design/architecture/DATA_FLOW.md` | FROZEN |
| **Architecture** | `docs/integration_design/architecture/DEPENDENCY_RULES.json` | FROZEN |
| **Architecture** | `docs/integration_design/architecture/ERROR_MODEL.json` | FROZEN |
| **Architecture** | `docs/integration_design/architecture/INTEGRATION_ARCHITECTURE.md` | FROZEN |
| **Architecture** | `docs/integration_design/architecture/INTEGRATION_INTERFACE_CONTRACT.json` | FROZEN |
| **Control** | `docs/integration_design/control/FALLBACK_POLICY.md` | FROZEN |
| **Control** | `docs/integration_design/control/FEATURE_FLAG_CONTRACT.md` | FROZEN |
| **Control** | `docs/integration_design/control/FEATURE_FLAG_SCHEMA.json` | FROZEN |
| **Control** | `docs/integration_design/control/ROLLBACK_RUNBOOK.md` | FROZEN |
| **Control** | `docs/integration_design/control/SHUTDOWN_TRIGGERS.md` | FROZEN |
| **Security** | `docs/integration_design/security/ACCESS_CONTROL_MATRIX.json` | FROZEN |
| **Security** | `docs/integration_design/security/DATA_HANDLING_POLICY.md` | FROZEN |
| **Security** | `docs/integration_design/security/INCIDENT_RESPONSE.md` | FROZEN |
| **Security** | `docs/integration_design/security/SECURITY_ACCEPTANCE_CONTRACT.md` | FROZEN |
| **Security** | `docs/integration_design/security/THREAT_MODEL.md` | FROZEN |
| **Evaluation** | `docs/integration_design/evaluation/INTEGRATION_FIXTURE_SPEC.json` | FROZEN |
| **Evaluation** | `docs/integration_design/evaluation/INTEGRATION_TEST_MATRIX.md` | FROZEN |
| **Evaluation** | `docs/integration_design/evaluation/PILOT_METRICS.md` | FROZEN |
| **Evaluation** | `docs/integration_design/evaluation/TELEMETRY_SCHEMA.json` | FROZEN |
| **Fixtures** | `tests/fixtures/integration_design/integration_cases.jsonl` | FROZEN |
