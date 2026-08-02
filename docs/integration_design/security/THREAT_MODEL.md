# Threat Model: Therapist Pilot Security Architecture

## 1. Executive Summary & Scope

This Threat Model establishes the comprehensive security analysis for the **Therapist Pilot** environment within the Clinical AI GraphRAG system. The therapist pilot allows authorized clinical personnel to query clinical guidelines, evidence-based practices, and receive AI-assisted therapeutic strategy suggestions.

### 1.1 In-Scope Capabilities
- Advisory RAG queries against approved clinical knowledge graphs.
- Ephemeral summarization of anonymized session notes.
- Therapist-facing evidence provenance and uncertainty metrics display.

### 1.2 Out-of-Scope Boundaries (Strict Anti-Requirements)
- **Zero Real Patient Data / PII**: No real patient health records or identifiable information.
- **Zero Raw Narrative Persistence**: No raw text of clinical notes stored in database or graph.
- **Zero Autonomous Clinical Action**: No direct patient interaction, diagnosis, or prescription.
- **Zero Production Graph Mutations**: Pilot operations are strictly read-only against approved knowledge graphs.

---

## 2. Threat Vector Deep-Dive (TM-01 through TM-15)

### TM-01: Unauthorized User Access
- **Description**: An unauthenticated user or unauthorized party attempts to call pilot APIs or view clinical advisor interfaces.
- **Attacker Profile**: External adversary, unauthorized employee, or compromised workstation.
- **Impact**: High. Disclosure of proprietary clinical knowledge structures and pilot metrics.
- **Mitigation**:
  - Mandatory OAuth2 / OIDC authentication with Short-Lived JWT Tokens (max 15 min lifetime).
  - Multi-Factor Authentication (MFA) required for all clinical staff access.
  - Role-Based Access Control (RBAC) enforced at API Gateway and service boundaries.
- **Verification Criteria**: Automated integration tests verifying 401 Unauthorized for unauthenticated requests and 403 Forbidden for missing pilot entitlements.

### TM-02: Personally Identifiable Information (PII) Ingress/Egress
- **Description**: Identifiable patient details (names, SSNs, phone numbers, emails, addresses, MRNs) introduced via query prompts or note uploads.
- **Attacker Profile**: User error by therapist, or malicious injection of patient records.
- **Impact**: Critical. Regulatory non-compliance (HIPAA/GDPR) and privacy breach.
- **Mitigation**:
  - Pre-execution deterministic regex matching (`gate_d/safety_policy.py`) for SSNs, phones, and emails triggering `PIIRejectedError`.
  - Secondary Named Entity Recognition (NER) anonymization pipeline prior to model prompt construction.
  - Egress sanitization filtering responses for unexpected PII patterns before returning to client.
- **Verification Criteria**: 100% rejection in synthetic benchmark tests containing synthetic PII strings; zero PII allowed into LLM context.

### TM-03: Prompt Injection & Instruction Overrides
- **Description**: Adversarial prompt engineering (direct or indirect via uploaded notes) designed to bypass safety boundaries, extract system prompts, or induce unauthorized behavior.
- **Attacker Profile**: Malicious user, compromised note source, or adversarial tester.
- **Impact**: High. Generation of unvetted advice, safety rule bypass, or system prompt leakage.
- **Mitigation**:
  - Strict input sanitization and template parameterization separating system instructions from user inputs.
  - Guardrail evaluation layers checking for prompt override patterns ("ignore previous instructions", jailbreaks).
  - Explicit system prompt instruction: "Never render diagnostic codes, prescribe medication, or output direct patient messaging."
- **Verification Criteria**: Security test suite executing known jailbreak payloads (DAN, multi-language bypass) achieving 0% policy bypass.

### TM-04: Tool Misuse & Parameter Tampering
- **Description**: Manipulation of AI agent tool invocation parameters to access unintended internal utilities or parameters.
- **Attacker Profile**: Malicious actor abusing agent tool execution runtime.
- **Impact**: High. Unauthorized resource query or unexpected system behavior.
- **Mitigation**:
  - Strict whitelisting of allowed tools for `THERAPIST_PILOT_USER` (read-only Graph RAG retrieval tool only).
  - Schema validation on all tool arguments with strict bounds checking.
  - Prohibition of dynamic tool generation or reflective execution.
- **Verification Criteria**: Automated schema validation checks rejecting invalid tool parameters and unauthorized tool name calls.

### TM-05: Secret Exposure & Credential Leakage
- **Description**: API keys, database credentials, or secret tokens exposed in logs, stack traces, error messages, or LLM context outputs.
- **Attacker Profile**: Insider threat, log scraper, or observer of application outputs.
- **Impact**: Critical. Compromise of underlying cloud infrastructure, model endpoints, or databases.
- **Mitigation**:
  - Centralized secret management (HashiCorp Vault / AWS Secrets Manager); credentials injected via environment at runtime without code exposure.
  - Redaction filter on standard logging outputs (`stdout`, `stderr`, audit trails) scrubbing API key formats and authorization headers.
  - Generic client-facing error messages preventing stack trace propagation.
- **Verification Criteria**: Static code analysis scanning for hardcoded secrets; automated log audits validating complete absence of tokens.

### TM-06: Cross-Pilot Data Leakage & Session Bleed
- **Description**: Information from one therapist's pilot session or specific `pilot_id` leaking into another therapist's active session or cache.
- **Attacker Profile**: Authenticated pilot user observing another therapist's query context.
- **Impact**: High. Confidentiality breach between pilot participants.
- **Mitigation**:
  - Strict tenant and session isolation enforced by passing `pilot_id` and `session_id` in all data access contexts.
  - Cache partitioning keying vector and GraphRAG cache by `(pilot_id, session_id)`.
  - Memory buffer flushing immediately upon session termination or timeout.
- **Verification Criteria**: Multi-tenant isolation test verifying user A cannot query or retrieve cached responses belonging to user B.

### TM-07: Audit Log Tampering & Suppression
- **Description**: Deletion, modification, or intentional suppression of audit events to conceal unauthorized activity or safety policy violations.
- **Attacker Profile**: Insider threat or compromised account attempting cover-up.
- **Impact**: High. Loss of accountability, failure of governance oversight.
- **Mitigation**:
  - Write-Once-Read-Many (WORM) storage architecture for audit logs (append-only log streams).
  - Cryptographic hash chaining on audit log records to detect deletion or alteration.
  - Centralized, restricted log forwarding to security SIEM inaccessible to standard pilot users or operators.
- **Verification Criteria**: Verification script checking cryptographic integrity of audit log chain; automated test demonstrating log modification rejection.

### TM-08: Novelty Promotion Pipeline Bypass
- **Description**: Attempting to force newly generated clinical insights or graph nodes into the production knowledge graph without passing clinical board review.
- **Attacker Profile**: Malicious or over-eager user trying to inject unverified knowledge into the main system.
- **Impact**: High. Pollution of validated clinical knowledge base with unverified claims.
- **Mitigation**:
  - Strict decoupling of pilot query engine from knowledge graph write APIs.
  - Candidate novelties routed exclusively to an isolated staging queue requiring multi-signature approval by `CLINICAL_REVIEWER`.
  - Zero direct write capability assigned to `THERAPIST_PILOT_USER`.
- **Verification Criteria**: Attempting direct node/edge creation via pilot API returns 403 Forbidden; novelty staging pipeline enforced.

### TM-09: Feature Flag & Safety Boundary Bypass
- **Description**: Circumventing the master feature flag `INTERNAL_CLINICAL_PILOT_READY` or sub-feature flags governing pilot capabilities.
- **Attacker Profile**: Authenticated user attempting to enable restricted or unreleased features.
- **Impact**: Critical. Execution of unvetted or disabled pilot functionality.
- **Mitigation**:
  - Server-side enforcement of feature flags at the API Gateway and core dispatcher logic.
  - Hard failure (`403 Pilot Disabled`) if `INTERNAL_CLINICAL_PILOT_READY` flag evaluates to false.
  - Immutability of feature flag status during request lifecycle.
- **Verification Criteria**: Automated integration test confirming all endpoint access attempts fail instantly when master flag is toggled off.

### TM-10: Unauthorized Production Activation & Model Promotion
- **Description**: Promoting pilot configurations, experimental prompts, or unvetted model versions directly to live clinical production.
- **Attacker Profile**: System operator error or unauthorized deployment script execution.
- **Impact**: Critical. Widespread deployment of unvalidated clinical AI to non-pilot environments.
- **Mitigation**:
  - Environment separation (Pilot Sandbox vs Production) with strict CI/CD gate checks.
  - Infrastructure-as-Code (IaC) deployment pipelines requiring dual-approval pull requests.
  - Hardcoded runtime assertions blocking production environment flags from loading pilot experimental models.
- **Verification Criteria**: Deployment gate check confirming production deployment fails without formal Governance Board sign-off artifact.

### TM-11: Graph Write & Knowledge Mutation Attempts
- **Description**: Injecting Cypher/SPARQL write commands or executing graph mutation API endpoints via pilot queries.
- **Attacker Profile**: Malicious user attempting data destruction or graph corruption.
- **Impact**: Critical. Degradation or corruption of foundational clinical knowledge graphs.
- **Mitigation**:
  - Graph database connection pools for pilot queries authenticated using read-only database credentials.
  - Query parser validation enforcing strict read-only query structures (e.g., `MATCH ... RETURN` only; blocking `CREATE`, `MERGE`, `SET`, `DELETE`).
- **Verification Criteria**: Automated tests sending Cypher write queries through pilot endpoints returning parser syntax/security error.

### TM-12: External Network Calls & Outbound Leakage
- **Description**: System or agent attempting unauthorized outbound HTTP/TCP calls to external third-party servers or non-whitelisted APIs.
- **Attacker Profile**: Prompt injection payload attempting data exfiltration via SSRF or webhook callback.
- **Impact**: High. Potential data exfiltration or external command & control execution.
- **Mitigation**:
  - Egress network filtering (Security Groups & Network Policies) restricting outbound traffic strictly to internal model services and databases.
  - Disabling dynamic URL fetching or network tools within the pilot agent runtime.
- **Verification Criteria**: Automated container sandbox test verifying outbound HTTP attempts to external IPs are dropped by firewall rules.

### TM-13: Unsafe OS Command & Process Execution
- **Description**: Execution of shell commands, process spawning, or system command injection via tool parameters or model output parsing.
- **Attacker Profile**: Malicious input payload exploiting shell execution vulnerabilities.
- **Impact**: Critical. Complete host/container compromise.
- **Mitigation**:
  - Complete elimination of shell invocation libraries (`subprocess` with `shell=True`, `os.system`) across application code.
  - Containerization with read-only root filesystems and non-root runtime users (`UID 10001`).
- **Verification Criteria**: Static code security analysis (Bandit/Semgrep) passing with zero shell execution findings; security tests verifying command injection payloads fail.

### TM-14: Stale Sessions & Session Hijacking
- **Description**: Replay of expired authentication tokens or hijacking of inactive therapist sessions.
- **Attacker Profile**: Attacker obtaining stale JWT token from client browser storage or network packet capture.
- **Impact**: Medium to High. Unauthorized access using legitimate credentials.
- **Mitigation**:
  - Short JWT access token expiration (15 minutes max) paired with idle session timeouts (15 minutes).
  - Refresh tokens bound to specific client fingerprint and IP address, stored in `HttpOnly`, `Secure`, `SameSite=Strict` cookies.
  - Instant token revocation list maintained in Redis for immediate session kill.
- **Verification Criteria**: Integration test confirming expired token usage returns 401; idle timeout enforces session termination.

### TM-15: Privilege Escalation (Horizontal & Vertical)
- **Description**: A `THERAPIST_PILOT_USER` attempting to perform operations assigned to `CLINICAL_REVIEWER`, `CONTENT_REVIEWER`, `SYSTEM_OPERATOR`, or `SECURITY_AUDITOR`.
- **Attacker Profile**: Authenticated therapist manipulating request parameters, headers, or API routes.
- **Impact**: High. Bypass of review workflows, audit access, or system configuration controls.
- **Mitigation**:
  - Fine-grained Access Control Matrix (RBAC/ABAC) evaluated at controller layer using validated JWT claims.
  - Zero trust model: Every endpoint explicitly checks caller role against resource permission matrix before execution.
  - Deny-by-default permission strategy.
- **Verification Criteria**: Automated role matrix test suite asserting that `THERAPIST_PILOT_USER` tokens receive 403 Forbidden when calling reviewer, operator, or auditor endpoints.

---

## 3. Threat Summary & Risk Matrix

| Threat ID | Threat Category | Target Asset | Severity | Primary Mitigation Control |
|---|---|---|---|---|
| TM-01 | Unauthorized User Access | API Gateway / UI | High | OAuth2/OIDC + Short-lived JWT + MFA |
| TM-02 | PII Ingress/Egress | LLM Context & Audit | Critical | Deterministic Regex + NER Sanitization (`SafetyPolicy`) |
| TM-03 | Prompt Injection | Agent Context | High | Parameterized Templates + Input Filtering |
| TM-04 | Tool Misuse | Agent Runtime | High | Whitelisted Tool Sets + Schema Validation |
| TM-05 | Secret Exposure | Application Logs | Critical | Centralized Vault + Log Redaction Filter |
| TM-06 | Cross-Pilot Data Leakage | Memory & Cache | High | Strict `pilot_id` & Session Isolation |
| TM-07 | Audit Log Tampering | Audit Store | High | Append-Only WORM Storage + Hash Chaining |
| TM-08 | Novelty Promotion Bypass | Knowledge Graph | High | Multi-Signature Review Pipeline Isolation |
| TM-09 | Feature Flag Bypass | Pilot Dispatcher | Critical | Server-Side `INTERNAL_CLINICAL_PILOT_READY` Check |
| TM-10 | Production Activation | CI/CD & Production | Critical | Dual-Approval IaC Gates & Environment Separation |
| TM-11 | Graph Write Attempts | Knowledge Base | Critical | Read-Only DB Credentials + Cypher Parser Restrictions |
| TM-12 | External Network Calls | Egress Firewall | High | Egress Network Policy Whitelisting |
| TM-13 | Unsafe OS Commands | OS Host Container | Critical | Container Read-Only Root + No Shell Exec |
| TM-14 | Stale Sessions | Auth Service | Medium | 15-min Token Expiry + Session Kill List |
| TM-15 | Privilege Escalation | Control Plane | High | Centralized RBAC Matrix Enforcement |
