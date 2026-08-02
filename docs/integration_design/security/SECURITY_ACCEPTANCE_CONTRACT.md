# Security Acceptance Contract: Therapist Pilot

## 1. Document Overview & Binding Authority

This Security Acceptance Contract defines the non-negotiable security prerequisites, operational boundaries, verification gates, and formal sign-off requirements for authorizing the launch and ongoing execution of the **Therapist Pilot**.

Compliance with this contract is mandatory. Any violation of the boundaries or failure to pass the verification gates will result in immediate revocation of pilot authorization and activation of the emergency kill-switch.

---

## 2. Mandatory Security Boundaries & Anti-Requirements

The Therapist Pilot system must strictly enforce the following five mandatory security boundaries at all times:

1. **Boundary 1: Zero Real Patient Data / PII**
   - No identifiable patient data (name, SSN, phone, email, address, MRN) may enter the system.
   - Enforced by `gate_d/safety_policy.py` deterministic regex scanning and secondary NER sanitization.

2. **Boundary 2: Zero Autonomous Clinical Decisions**
   - System outputs are strictly advisory for authorized human therapists.
   - Engine output must never issue diagnoses, treatment plans, or prescription advice.
   - Enforced by safety policy checks, system prompts, and UI disclaimer banners.

3. **Boundary 3: Zero Knowledge Graph Mutations**
   - Pilot execution must operate on a strictly read-only database connection pool.
   - Cypher/SPARQL write commands (`CREATE`, `MERGE`, `SET`, `DELETE`) are blocked at the query parsing layer.

4. **Boundary 4: Zero External Network Calls**
   - Agent execution runtime must operate in an egress-blocked sandbox environment.
   - Outbound HTTP/TCP calls to non-whitelisted external IPs are dropped by container network policies.

5. **Boundary 5: Zero Raw Clinical Narrative Storage**
   - Raw text of uploaded session notes or clinical prompts must never be persisted to disk, databases, or long-term caches.
   - Application memory buffers must be zeroed immediately after request processing or session termination.

---

## 3. Pre-Deployment Security Gates & Prerequisites

The condition `INTERNAL_CLINICAL_PILOT_READY` can only be set to `true` when all prerequisite gates are formally audited and closed:

- **Gate A (Foundation Safety & Compliance)**: Passed 100% of baseline compliance and privacy audits.
- **Gate B (Architecture & Data Flow)**: Network isolation, tenant isolation, and RBAC matrix verified.
- **Gate C (Knowledge Base & Graph RAG)**: Graph accuracy audited and read-only query pool configured.
- **Gate D (Safety, Governance & Evaluation)**: Passed 100% of the 60 synthetic safety test cases defined in the Gate D test matrix.
- **Feature Flag Governance**: Master feature flag `INTERNAL_CLINICAL_PILOT_READY` active and verified.
- **Legacy Fallback & Rollback**: Functional manual fallback and documented rollback procedures operational.

---

## 4. Security Performance Metrics (SLOs / SLAs)

| Security Control | Target SLO / SLA | Measurement Method | Failure Threshold | Action on Failure |
|---|---|---|---|---|
| PII Detection & Rejection | 100.0% Rejection Rate | Synthetic PII Test Benchmark | Any accepted PII string (>0) | Immediate Pilot Suspension |
| Prompt Injection Resistance | 100.0% Block Rate | Adversarial Payload Suite | Any successful prompt override | Emergency Patch & Re-audit |
| Audit Log Coverage | 100.0% Event Logging | Automated Log Integrity Check | Missing audit record (<100%) | Halt API processing |
| Unauthorized Access Block | 100.0% Enforcement | Role Permutation Integration Tests | Any 403/401 bypass | Disable affected endpoint |
| Session Timeout Enforcement | < 15 Minutes Inactivity | Automated Session Expiry Verification | Session active > 15m idle | Kill active session pool |
| Graph Write Blocking | 100.0% Query Rejection | Cypher Mutation Injection Suite | Any executed write query | Re-point to read-only DB user |

---

## 5. Automated Verification Test Suites

Before deployment, the system must execute and pass the following continuous automated security test suites:

1. **`test_safety_policy.py`**: Executes deterministic tests against `gate_d/safety_policy.py` validating PII regex detection, forbidden keyword blocking, and `PIIRejectedError` / `SafetyViolationError` throwing.
2. **`test_access_control_matrix.py`**: Simulates calls across all API endpoints using tokens for each of the 5 roles (`THERAPIST_PILOT_USER`, `CLINICAL_REVIEWER`, `CONTENT_REVIEWER`, `SYSTEM_OPERATOR`, `SECURITY_AUDITOR`), verifying exact alignment with `ACCESS_CONTROL_MATRIX.json`.
3. **`test_threat_model_mitigations.py`**: Executes automated exploit attempts against all 15 threat vectors defined in `THREAT_MODEL.md`.
4. **`test_audit_immutability.py`**: Verifies cryptographic hash chain integrity of the audit log stream and tests write-only enforcement.

---

## 6. Formal Governance Sign-Off Matrix

The therapist pilot MAY NOT activate without formal, cryptographic/written sign-off from all required stakeholders:

| Stakeholder Role | Representative / Board | Required Sign-Off Artifact | Verification Status |
|---|---|---|---|
| Lead Clinical Officer | Clinical Governance Board | `docs/internal_pilot/CLINICAL_SIGN_OFF.md` | PENDING FINAL AUDIT |
| Lead Safety Engineer | Safety Engineering Team | `docs/internal_pilot/SAFETY_SIGN_OFF.md` | PENDING FINAL AUDIT |
| Compliance & Privacy Officer | Compliance Board | `docs/internal_pilot/COMPLIANCE_SIGN_OFF.md` | PENDING FINAL AUDIT |
| Lead Security Auditor | Independent Security Team | `docs/integration_design/security/SECURITY_AUDIT_SIGN_OFF.md` | PENDING FINAL AUDIT |
| Chief System Operator | Operations Team | `docs/internal_pilot/OPERATIONS_SIGN_OFF.md` | PENDING FINAL AUDIT |

---

## 7. Contract Violations & Enforcement Actions

- **Severity 1 Violation (PII Leakage, Prompt Override, Unauthorized Data Mutation)**:
  - Automated kill-switch toggles `INTERNAL_CLINICAL_PILOT_READY = false`.
  - All active therapist sessions terminated immediately.
  - Incident Response protocol (`INCIDENT_RESPONSE.md`) triggered at SEV-1 level.
- **Severity 2 Violation (Audit Disruption, Stale Session Persistence)**:
  - System Operator notified via high-priority alert.
  - Pilot access restricted to read-only diagnostic mode until resolved.
