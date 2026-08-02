# Security Incident Response Plan: Therapist Pilot

## 1. Plan Overview & Objectives

This Incident Response Plan defines the mandatory operational procedures for detecting, containing, investigating, and remediating security incidents occurring within the **Therapist Pilot** environment.

### Primary Objectives
1. **Immediate Containment**: Prevent unauthorized access, data exfiltration, or safety boundary violations within seconds of detection.
2. **Clinical Safety Protection**: Guarantee zero exposure of real patient data and zero unvetted clinical advice generation.
3. **Forensic Integrity**: Preserve immutable evidence and audit log chains for forensic analysis.
4. **Structured Recovery**: Re-enable pilot features only after formal remediation verification and Governance Board approval.

---

## 2. Incident Severity Classification

Incidents are classified into four severity tiers based on clinical safety risk, data privacy impact, and system integrity:

| Severity Level | Definition & Criteria | Examples | Response SLA | Target Containment |
|---|---|---|---|---|
| **SEV-1 (Critical)** | Active safety boundary failure, PII leakage, prompt injection bypass, or unauthorized graph mutation. | PII accepted into model context; prompt override producing unvetted advice; successful graph write. | Immediate (< 5 min) | < 1 minute (Automated Kill-Switch) |
| **SEV-2 (High)** | Attempted security control bypass, unauthorized external network call, or audit log stream disruption. | Repeated jailbreak attempts; firewall blocked outbound call; audit WORM write failure. | < 15 minutes | < 15 minutes |
| **SEV-3 (Medium)** | RBAC authorization failure spikes, stale session persistence, or suspicious query patterns. | Multiple 403 Forbidden errors from single user; session token active post-idle timeout. | < 1 hour | < 2 hours |
| **SEV-4 (Low)** | Non-critical security telemetry anomaly or minor documentation/policy mismatch. | Discrepancy in log formatting; non-blocking API rate limit breach. | < 24 hours | < 48 hours |

---

## 3. Incident Triggers & Automated Detection

The following trigger events automatically initiate the Incident Response Workflow:

1. **Trigger: PII Ingress Event** (`SafetyPolicy` raises `PIIRejectedError` or NER flags PII).
2. **Trigger: Prompt Injection Attack** (Guardrail engine detects high-confidence jailbreak score).
3. **Trigger: Graph Mutation Attempt** (Read-only database connection receives Cypher write command).
4. **Trigger: Master Feature Flag Bypass Attempt** (Request routed with `INTERNAL_CLINICAL_PILOT_READY = false`).
5. **Trigger: Audit Log Integrity Anomaly** (Hash chain verification check fails on audit stream).
6. **Trigger: Unauthorized External Egress Call** (Egress network policy drops outbound packet).
7. **Trigger: Privilege Escalation Attempt** (`THERAPIST_PILOT_USER` attempts call to reviewer or operator endpoint).

---

## 4. Immediate Containment Protocols

When a SEV-1 or high-confidence SEV-2 trigger fires, automated and manual containment controls activate immediately:

```
[Trigger Detected] ──► [Automated Guardrail] ──► Toggle Feature Flag (INTERNAL_CLINICAL_PILOT_READY = false)
                                            ├──► Revoke Active Session Tokens (Redis Blacklist)
                                            ├──► Freeze Staging Knowledge Graph Queues
                                            └──► Page On-Call System Operator & Security Auditor
```

### 4.1 Automated Master Kill-Switch
- System guardrails automatically flip `INTERNAL_CLINICAL_PILOT_READY = false` in global configuration.
- All subsequent incoming API requests to `/api/v1/pilot/*` endpoints immediately receive `403 Pilot Disabled`.

### 4.2 Session Termination & Token Blacklisting
- All active JWT access tokens associated with the affected user or pilot instance are pushed to the Redis Token Blacklist.
- Websocket connections and session memory buffers are immediately terminated and zeroed out.

### 4.3 Sandbox Lockdown
- If an outbound network call or command execution attempt is detected, the affected application container instance is isolated and quarantined for memory dump analysis.

---

## 5. Roles & Escalation Path

```
                 +-----------------------------------+
                 |    Clinical Governance Board      |
                 | (Strategic Oversight & Approval) |
                 +-----------------+-----------------+
                                   ^
                                   | Formal Escalation
                                   v
+----------------------------------+----------------------------------+
|                                                                     |
|    +------------------------+          +-----------------------+    |
|    |    SECURITY_AUDITOR    | <------> |    SYSTEM_OPERATOR    |    |
|    | (Forensics & Compliance)|          | (Ops & Containment)   |    |
|    +------------------------+          +-----------------------+    |
|                                                                     |
+----------------------------------+----------------------------------+
                                   ^
                                   | PagerDuty Alert
                                   v
                 +-----------------------------------+
                 |    Automated System Guardrails    |
                 +-----------------------------------+
```

1. **System Operator (`SYSTEM_OPERATOR`)**: Responsible for immediate infrastructure containment, verifying kill-switch status, and maintaining service stability.
2. **Security Auditor (`SECURITY_AUDITOR`)**: Leads forensic investigation, extracts immutable audit logs, analyzes attack vectors, and authors the incident report.
3. **Clinical Reviewer (`CLINICAL_REVIEWER`)**: Evaluates potential clinical impact or safety risk associated with the incident.
4. **Clinical Governance Board**: Receives formal incident briefing, reviews post-mortem, and holds sole authority for authorizing pilot re-enablement.

---

## 6. Forensic & Investigation Procedures

1. **Audit Stream Extraction**: `SECURITY_AUDITOR` retrieves append-only WORM audit logs for the relevant `trace_id`, `pilot_id`, and `session_id` time window.
2. **Cryptographic Verification**: Verify audit chain SHA-256 signatures to guarantee log evidence has not been tampered with.
3. **Memory & Context Reconstruction**: Reconstruct the exact sequence of prompt parameters, safety boundary checks, and system events leading to the trigger without logging raw PII.
4. **Root Cause Analysis (RCA)**: Determine whether the incident resulted from malicious intent, prompt engineering vulnerability, software flaw, or configuration drift.

---

## 7. Remediation & Post-Mortem Requirements

Within **24 hours** of a SEV-1 or SEV-2 incident containment, the response team must produce a formal Post-Mortem Document containing:

- **Timeline**: Minute-by-minute breakdown of detection, containment, and notification steps.
- **Root Cause**: Detailed technical analysis of the vulnerability or trigger mechanism.
- **Impact Assessment**: Confirmation of data exfiltration status (verifying zero PII leaked) and clinical safety status.
- **Corrective Action Plan**: Specific engineering tasks (code fixes, safety policy updates, regex enhancements, test additions) required to prevent recurrence.
- **Regression Test Addition**: New automated test cases added to `test_threat_model_mitigations.py` or `gate_d/safety_policy.py` reproducing the incident scenario.

---

## 8. Recovery & Re-Enablement Criteria

The therapist pilot MAY NOT be re-enabled (restoring `INTERNAL_CLINICAL_PILOT_READY = true`) until ALL of the following criteria are satisfied:

1. **Remediation Code Deployed**: Corrective patch merged into main codebase after dual-engineer code review.
2. **Automated Verification Passed**: 100% pass rate achieved across all security test suites (`Gate A`, `Gate B`, `Gate C`, `Gate D`, and new regression tests).
3. **Audit Integrity Confirmed**: Formal verification that all audit channels and logging pipelines are operating normally.
4. **Formal Sign-Off**: Written authorization signed by the Lead Security Auditor and the Chair of the Clinical Governance Board.
