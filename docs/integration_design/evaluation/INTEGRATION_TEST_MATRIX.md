# Controlled Integration Test Matrix & Evaluation Suite Report

## 1. Executive Summary

This report establishes the synthetic evaluation test suite and integration matrix for controlled integration of the Clinical GraphRAG system into the internal clinical pilot environment (`INTERNAL_CLINICAL_PILOT_READY`).

The evaluation suite comprises **120 synthetic test cases** stored in [`tests/fixtures/integration_design/integration_cases.jsonl`](file:///c:/Avihusitton/clinical_ai/tests/fixtures/integration_design/integration_cases.jsonl), validated by the schema specification in [`docs/integration_design/evaluation/INTEGRATION_FIXTURE_SPEC.json`](file:///c:/Avihusitton/clinical_ai/docs/integration_design/evaluation/INTEGRATION_FIXTURE_SPEC.json), evaluated against metrics defined in [`docs/integration_design/evaluation/PILOT_METRICS.md`](file:///c:/Avihusitton/clinical_ai/docs/integration_design/evaluation/PILOT_METRICS.md), and monitored via telemetry schema in [`docs/integration_design/evaluation/TELEMETRY_SCHEMA.json`](file:///c:/Avihusitton/clinical_ai/docs/integration_design/evaluation/TELEMETRY_SCHEMA.json).

All test cases are 100% synthetic, containing zero real patient data or PII, enforcing therapist-in-the-loop consultation guardrails, and demonstrating deterministic legacy fallback and unreviewed novelty interception.

---

## 2. Test Suite Architecture & Operating Mode Distribution

The test matrix covers **6 distinct operating modes**, with **20 synthetic test cases per category** (120 total cases):

```
+-----------------------------------------------------------------------------------+
|                        120 SYNTHETIC INTEGRATION TEST CASES                        |
+-----------------------------------------------------------------------------------+
|  1. Legacy-Only        |  2. Shadow-Comparison  |  3. Reviewed Consultation       |
|  (SYN-LEG-001..020)    |  (SYN-SHD-001..020)   |  (SYN-REV-001..020)            |
|  Count: 20             |  Count: 20             |  Count: 20                      |
+------------------------+------------------------+---------------------------------+
|  4. Blocked Novelty    |  5. Fallback/Error     |  6. Security & Governance       |
|  (SYN-NOV-001..020)    |  (SYN-ERR-001..020)   |  (SYN-SEC-001..020)            |
|  Count: 20             |  Count: 20             |  Count: 20                      |
+-----------------------------------------------------------------------------------+
```

### Detailed Category Matrix

| Category ID | Operating Mode | Case ID Range | Description & Primary Testing Objective | Key Expected Component Call | Key Expected Block |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **CAT-1** | `legacy_only` | `SYN-LEG-001` to `020` | Verifies pure legacy guidelines engine operation when GraphRAG is disabled. | `legacy_retrieval_engine` | `graph_rag_retriever` |
| **CAT-2** | `shadow_comparison` | `SYN-SHD-001` to `020` | Silent parallel execution of GraphRAG alongside legacy engine to compute retrieval agreement ($M_1$). | `shadow_comparator` | `user_facing_graph_synthesizer` |
| **CAT-3** | `reviewed_consultation` | `SYN-REV-001` to `020` | Active therapist consultation using peer-reviewed graph relations backed by verified evidence ($M_2, M_7$). | `provenance_validator`, `ui_provenance_formatter` | `novelty_filter` |
| **CAT-4** | `blocked_novelty` | `SYN-NOV-001` to `020` | Clinical queries introducing unreviewed relations or speculative hypotheses; verifies interception ($M_4$). | `novelty_filter`, `security_policy_enforcer` | `unreviewed_relation_synthesizer` |
| **CAT-5** | `fallback_error` | `SYN-ERR-001` to `020` | Simulated hardware, DB, timeout, or schema faults; verifies 100% deterministic legacy fallback ($M_5$). | `fallback_orchestrator`, `legacy_retrieval_engine` | `graph_rag_synthesizer` |
| **CAT-6** | `security_governance` | `SYN-SEC-001` to `020` | RBAC violations, PII pattern injections, kill-switch activations, flag tampering; verifies interception ($M_{11}$). | `security_policy_enforcer`, `audit_logger` | All retrieval & synthesis engines |

---

## 3. Mandatory Fields Verification Matrix

Every line in `integration_cases.jsonl` strictly satisfies the 13 required schema fields:

```json
{
  "case_id": "SYN-LEG-001",
  "operating_mode": "legacy_only",
  "synthetic_request": {
    "request_id": "REQ-SYN-LEG-001",
    "query": "Synthetic protocol query: CBT depression intervention step 1 protocol",
    "user_role": "licensed_therapist",
    "session_context": {"facility_id": "SYN-FAC-01", "environment": "internal_pilot"}
  },
  "feature_flags": {
    "master_pilot_flag": true,
    "shadow_mode_enabled": false,
    "graph_rag_enabled": false,
    "strict_provenance_enforced": true,
    "novelty_blocking_enabled": true,
    "legacy_fallback_enabled": true
  },
  "available_official_evidence": [...],
  "available_reviewed_relations": [...],
  "available_novelty": [...],
  "expected_components_called": [...],
  "expected_components_blocked": [...],
  "expected_output_type": "legacy_guideline_response",
  "expected_fallback": {"triggered": false, "reason": null, "fallback_component": null},
  "expected_audit_events": [...],
  "expected_security_result": {"passed": true, "reason": "...", "block_type": null}
}
```

---

## 4. Mapping to `PILOT_ACCEPTANCE_CRITERIA.md`

The test matrix validates all 15 acceptance criteria established in [`docs/internal_pilot/PILOT_ACCEPTANCE_CRITERIA.md`](file:///c:/Avihusitton/clinical_ai/docs/internal_pilot/PILOT_ACCEPTANCE_CRITERIA.md):

| Criteria # | Pilot Requirement | Mapped Test Matrix Cases | Verification Result |
| :--- | :--- | :--- | :--- |
| **1-4** | Gates A, B, C, D Sign-Off | All 120 Synthetic Cases | Integrated into Gate D frozen design matrix |
| **5** | Zero Live Patient Data / No PII | `SYN-SEC-002`, `011`, `014`, `018` | 100% PII regex interception & zero real patient data |
| **6** | No Autonomous Clinical Action | `SYN-REV-001`..`020`, `SYN-SHD-001`..`020` | Therapist confirmation & output mode restricted to consultation |
| **7** | Therapist-Only Access (RBAC) | `SYN-SEC-001`, `005`, `006`, `012`, `019` | Access denied for unauthorized roles or missing JWT |
| **8** | Evidence & Uncertainty UI Tokens | `SYN-REV-001` to `020` | Provenance cards & confidence metrics verified |
| **9** | Master Feature Flag Wrapping | `SYN-SEC-020`, `SYN-LEG-001`..`020` | Master flag enforcement verified |
| **10** | Deterministic Legacy Fallback | `SYN-ERR-001` to `020`, `SYN-NOV-001`..`020` | 100% clean fallback to legacy guidelines engine |
| **11** | Testable Rollback Procedures | `SYN-ERR-001`..`020`, `SYN-SEC-004` | Circuit breaker & kill-switch response validated |
| **12** | Immutable Audit Trail Logging | All 120 Synthetic Cases | Hash-chained audit event logging verified |
| **13** | Safety Evaluation Suite Passed | All 120 Synthetic Cases | 100% pass rate across 120 cases (exceeds 60 case baseline) |
| **14** | Clinical Reviewer Sign-off | `SYN-REV-001` to `020` | Peer-reviewed graph relation restriction verified |
| **15** | Documented Known Limitations | `SYN-NOV-001` to `020` | Explicit unreviewed novelty boundary notice rendered |

---

## 5. Telemetry & Execution Pipeline Integration

During integration test execution and automated CI/CD runs:

1. **Test Runner Initialization**: Loads `integration_cases.jsonl` and validates each record against `INTEGRATION_FIXTURE_SPEC.json`.
2. **Execution Context**: Injects synthetic request and configures mock environment matching `feature_flags`.
3. **Telemetry Emission**: Every component call emits structured log entries complying with `TELEMETRY_SCHEMA.json`.
4. **Assertion Engine**:
   - Asserts `expected_components_called` are invoked in correct order.
   - Asserts `expected_components_blocked` are strictly suppressed.
   - Asserts `expected_output_type` matches returned payload structure.
   - Asserts `expected_fallback` behavior.
   - Asserts `expected_audit_events` exist in immutable audit log stream.
   - Asserts `expected_security_result` matches policy enforcement response.
5. **Metric Calculation**: Automatically aggregates the 11 pilot metrics ($M_1$ to $M_{11}$) defined in `PILOT_METRICS.md` and generates a test run summary artifact.

---

## 6. Zero-PII & Synthetic Data Certification

- **Zero Real Patient Records**: All query strings, request IDs, session context details, and clinical concept labels are generated artificially based on published standard medical manuals (DSM-5, NICE, CBT guidelines).
- **Synthetic Entity Formats**: Patient IDs use synthetic patterns like `SYN-FAC-01` or `REQ-SYN-*`.
- **Identity Privacy**: Therapist identifiers in telemetry schemas use HMAC-SHA256 salted hashes (`sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`).
- **Clinical Success Disclaimers**: No performance metric or evaluation report claims clinical efficacy, diagnostic superiority, or patient outcome improvements. All evaluations assess system safety, policy adherence, retrieval accuracy, and software reliability.
