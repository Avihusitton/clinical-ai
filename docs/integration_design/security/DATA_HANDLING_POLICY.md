# Data Handling & Privacy Policy: Therapist Pilot

## 1. Core Principles & Mandates

The Therapist Pilot operates under strict data protection, privacy, and clinical safety constraints. All pilot participants and technical components must strictly adhere to the following principles:

1. **Zero Real Patient Data**: No real patient health records, personally identifiable information (PII), or protected health information (PHI) are permitted in the system. All inputs must be synthetic or fully anonymized.
2. **Zero Raw Clinical Narrative Persistence**: Raw clinical text, verbatim transcripts, and unscrubbed session notes are strictly ephemeral. The system must never store raw clinical narratives in persistent databases, caches, or knowledge graphs.
3. **Data Minimization**: The system processes and retains only the minimum data necessary to perform advisory GraphRAG retrieval and temporary context generation.
4. **Least Privilege Data Access**: Users and microservices possess only the minimum data read/write entitlements required for their defined role.

---

## 2. Authentication & Authorization

### 2.1 Identity & Authentication
- All users must authenticate via an Enterprise Identity Provider (IdP) supporting SAML 2.0 / OpenID Connect (OIDC) with mandatory Multi-Factor Authentication (MFA).
- Successful authentication produces a short-lived RSA-256 signed JSON Web Token (JWT) with an access token lifetime of **15 minutes**.

### 2.2 Role-Based Access Control (RBAC)
- Authorization is evaluated centrally at the API Gateway and at service-level controllers using validated JWT claims.
- The 5 pilot roles (`THERAPIST_PILOT_USER`, `CLINICAL_REVIEWER`, `CONTENT_REVIEWER`, `SYSTEM_OPERATOR`, `SECURITY_AUDITOR`) are mapped directly to endpoints as defined in `ACCESS_CONTROL_MATRIX.json`.
- Requests lacking mandatory claims (`sub`, `role`, `pilot_id`, `session_id`, `mfa_verified`) are immediately rejected (`401 Unauthorized`).

---

## 3. PII Rejection & Input Sanitization Protocol

### 3.1 Deterministic Pre-Filtering
Before any request is passed to language models or vector search engines, it passes through the `SafetyPolicy` engine (`gate_d/safety_policy.py`).

```
User Input ──► [SafetyPolicy Regex Scanner] ──► PII Detected? ──► YES ──► Throw PIIRejectedError (Abort & Log)
                                                          │
                                                         NO
                                                          ▼
                                            [NER Anonymization Pipeline]
                                                          │
                                                          ▼
                                            [LLM Context Construction]
```

- **Regex Checks**: Scans for SSNs (`\d{3}-\d{2}-\d{4}`), Phone Numbers (`\d{3}-\d{3}-\d{4}`), Email addresses, and Medical Record Numbers (MRNs).
- **Behavior on Match**: Raises `PIIRejectedError` instantly. The request is aborted before model invocation, and a generic error message ("PII detected in request. Patient data must be fully anonymized.") is returned to the user.
- **Safety Violation Keyword Scanning**: Blocks forbidden terms ("diagnosis", "diagnose", "prescribe", "medication", "treatment decision", "suicide", "crisis"), raising `SafetyViolationError`.

### 3.2 Secondary Anonymization Layer
- If regex checks pass, a secondary Named Entity Recognition (NER) pipeline converts potential proper nouns (names, locations, dates) into synthetic placeholders (e.g., `[PATIENT_A]`, `[DATE_X]`).

---

## 4. Multi-Tenant & Session Isolation

### 4.1 Pilot ID Isolation (`pilot_id`)
- Every pilot request is bound to a unique `pilot_id` representing the specific pilot instance.
- All database queries, vector similarity searches, and graph retrieval operations enforce mandatory `WHERE pilot_id = :request_pilot_id` filter predicates.
- Data cross-contamination between different pilot instances or users is strictly impossible at the query layer.

### 4.2 Session Isolation (`session_id`)
- Context buffers, intermediate GraphRAG search results, and agent memory state are keyed exclusively by `session_id`.
- Active session state is maintained in-memory (or in encrypted short-lived Redis session stores) with an automatic **15-minute inactivity TTL**.
- When a therapist logs out or the session times out, the corresponding session memory buffer is explicitly purged and garbage collected.

---

## 5. Secret Handling & Credentials Management

### 5.1 Storage & Injection
- Hardcoding credentials, API keys, database connection strings, or signing certificates in code or configuration files is strictly forbidden.
- Secrets are stored in a centralized Secret Manager (e.g., HashiCorp Vault / AWS Secrets Manager) and dynamically injected into service containers at runtime via environment variables or secret mounts.

### 5.2 Environmental & Log Protection
- Standard logging frameworks (`logging`, `stdout`, `stderr`) are wrapped with a `RedactingFormatter` that automatically scrubs strings matching API key patterns (`sk-`, `bearer`, `eyJ...`).
- Direct reading of `.env` files or system environment variables by unapproved scripts is prohibited.

---

## 6. Safe Logging & Audit Immutability

### 6.1 Safe Logging Requirements
- **Allowed Log Fields**: Timestamp, `trace_id`, `pilot_id`, masked user ID (`usr_***`), endpoint path, HTTP status code, latency (ms), safety policy violation codes.
- **Forbidden Log Fields**: Prompt text, raw session notes, raw LLM outputs, full user query strings, JWT tokens, authorization headers.

### 6.2 Audit Trail Immutability
- Audit events are written to an append-only Write-Once-Read-Many (WORM) storage bucket.
- Each audit log entry is linked to the previous entry using SHA-256 hash chaining to form an immutable tamper-evident log stream.
- Deletion or modification of audit log records is restricted even for `SYSTEM_OPERATOR` accounts; only `SECURITY_AUDITOR` accounts have read access to full audit streams.

---

## 7. Access Revocation & Session Termination

### 7.1 Immediate Access Revocation
- In the event of a security incident, role change, or compromised account, system operators or automated guardrails can immediately revoke access.
- Revocation revokes the user's active JWT tokens by pushing the `session_id` and user `sub` to a high-priority Redis Token Blacklist.
- API Gateways check the Redis blacklist on every incoming request, ensuring sub-second revocation enforcement.

### 7.2 Emergency Master Deactivation
- Toggling the master feature flag `INTERNAL_CLINICAL_PILOT_READY` to `false` immediately disables all pilot endpoints globally, causing all active and new requests to fail safely with `403 Pilot Disabled`.

---

## 8. Data Retention & Purge Policy

### 8.1 Data Lifecycle Table

| Data Category | Storage Location | Retention Period | Purge Trigger / Mechanism |
|---|---|---|---|
| Ephemeral Prompt / Query Context | Application RAM / Temp Cache | Duration of Request (max 30s) | Immediate memory zeroing post-response |
| Session Memory Buffer | Redis (In-Memory, Encrypted) | 15 Minutes (Idle) / Max 8 Hours | Session logout or TTL expiry |
| Anonymized Session Summaries | Temporary Staging Store | 24 Hours | Automated cron purge script |
| Safety & PII Rejection Logs | Audit WORM Store | 90 Days | Automated lifecycle transition |
| System Performance Metrics | Prometheus / Telemetry DB | 30 Days | Automated rolling window deletion |
| Knowledge Graph Candidate Insights | Staging Queue | 14 Days | Clinical Governance review approval/rejection |

### 8.2 Secure Purge Protocol
- When data reaches the end of its retention window, automated purge routines execute secure deletion (`shred` / crypto-shredding by destroying the encryption key protecting the partition).
- Purge execution events are logged in the immutable audit trail for compliance verification.
