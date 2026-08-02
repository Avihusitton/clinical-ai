# Internal Pilot Evaluation Metrics Framework

## 1. Overview & Governance Constraints

This document defines the quantitative metrics framework for monitoring and evaluating the system during controlled integration testing and the internal pilot phase (`INTERNAL_CLINICAL_PILOT_READY`).

### Key Governance Principles
- **No Clinical-Success Claims**: Metrics evaluate system technical performance, retrieval accuracy, governance enforcement, safety guardrails, and therapist UX—**never** clinical efficacy or patient health outcomes.
- **Zero Real Patient Data**: All baseline evaluations and telemetry pipelines process 100% synthetic protocol queries and simulated sessions.
- **Therapist-in-the-Loop Safeguards**: The system functions strictly as a decision-support consultation tool for licensed internal clinical staff. Autonomous clinical decisions are strictly prohibited.

---

## 2. Core Pilot Metrics Specification

The internal pilot measures 11 primary operational metrics categorized across 4 key evaluation pillars:

| Metric Category | Metric Name | SLA Target / Threshold | Telemetry Data Source |
| :--- | :--- | :--- | :--- |
| **Retrieval & Evidence Accuracy** | 1. Retrieval Agreement | ≥ 85.0% overlap in shadow mode | `telemetry_event.retrieval_event` |
| | 2. Evidence Coverage | 100.0% of output claims backed by verified evidence | `telemetry_event.evidence_verification_event` |
| | 3. Unsupported-Claim Rate | 0.0% (Zero tolerance for unbacked assertions) | `telemetry_event.evidence_verification_event` |
| **Governance & Safety** | 4. Novelty-Block Rate | 100.0% of unreviewed relations blocked | `telemetry_event.novelty_block_event` |
| | 5. Fallback Success Rate | 100.0% clean fallback to legacy on error | `telemetry_event.fallback_event` |
| | 6. Audit Completeness | 100.0% immutable event logging & hash integrity | `telemetry_event.audit_logging_event` |
| | 7. Security-Block Rate | 100.0% interception of RBAC/PII/flag violations | `security_alert.security_event` |
| **Therapist UX & Transparency** | 8. Uncertainty Visibility | 100.0% display of confidence & provenance scores | `telemetry_event.therapist_interaction_event` |
| | 9. Therapist Override Rate | Monitored baseline (< 15.0% modification rate) | `telemetry_event.therapist_interaction_event` |
| **System Performance** | 10. End-to-End Latency | p95 < 2,500 ms (graph + vector + synthesis) | `telemetry_event.performance_event` |
| | 11. System Error Rate | < 0.5% unhandled errors (100% fallback handled) | `telemetry_event.performance_event` |

---

## 3. Detailed Metric Definitions & Mathematical Formulas

### 3.1 Retrieval Agreement Rate ($M_1$)
- **Definition**: The percentage overlap between documents/nodes retrieved by the GraphRAG engine and the baseline legacy vector retrieval engine during shadow comparison mode.
- **Formula**:
  $$M_1 = \frac{1}{N} \sum_{i=1}^{N} \frac{|R_{\text{GraphRAG}}^{(i)} \cap R_{\text{Legacy}}^{(i)}|}{|R_{\text{Legacy}}^{(i)}|}$$
- **Measurement Method**: Calculated in shadow comparison mode (`SYN-SHD-*`) by the `shadow_comparator` module. Logged via `AUDIT_COMPARISON_LOGGED`.
- **Pilot Acceptance Alignment**: Verifies that GraphRAG preserves baseline knowledge grounding while adding structured graph relationships.

### 3.2 Evidence Coverage Ratio ($M_2$)
- **Definition**: The proportion of generated protocol suggestions whose constituent clinical assertions are directly mapped to an official, verified evidence document ID in the knowledge base.
- **Formula**:
  $$M_2 = \frac{\text{Count of Assertions with Verified Provenance Links}}{\text{Total Count of Generated Assertions}} \times 100\%$$
- **Target**: **100.0%**. Every assertion presented to the therapist must display explicit provenance.

### 3.3 Unsupported-Claim Rate ($M_3$)
- **Definition**: The rate at which the synthesis engine generates statements without verified source provenance or official guideline citations.
- **Formula**:
  $$M_3 = 100\% - M_2$$
- **Target**: **0.0%**. Any response containing unsupported assertions triggers a provenance validation breach alert.

### 3.4 Novelty-Block Rate ($M_4$)
- **Definition**: The percentage of unreviewed candidate graph relations or speculative novel hypotheses correctly intercepted and blocked by the governance safety layer.
- **Formula**:
  $$M_4 = \frac{\text{Successfully Blocked Unreviewed Relations}}{\text{Total Unreviewed Relations Encountered}} \times 100\%$$
- **Target**: **100.0%**. Unreviewed novelty must never reach therapist-facing consultation outputs.

### 3.5 Fallback Success Rate ($M_5$)
- **Definition**: The probability that a subsystem error (Graph DB timeout, schema validation failure, service disconnect) results in a seamless, deterministic fallback to the legacy guidelines engine without user-facing crash or output corruption.
- **Formula**:
  $$M_5 = \frac{\text{Successful Legacy Fallbacks}}{\text{Total Triggered Subsystem Errors}} \times 100\%$$
- **Target**: **100.0%**. Directly enforces Item 10 of `PILOT_ACCEPTANCE_CRITERIA.md`.

### 3.6 Audit Completeness Ratio ($M_6$)
- **Definition**: The ratio of end-to-end user transactions with fully intact, sequentially linked, immutable audit log records.
- **Formula**:
  $$M_6 = \frac{\text{Transactions with Complete Audit Trail & Valid Hash Chain}}{\text{Total Processed Transactions}} \times 100\%$$
- **Target**: **100.0%**. Ensures full traceability for regulatory and safety reviews.

### 3.7 Uncertainty Visibility Rate ($M_7$)
- **Definition**: The percentage of therapist-facing consultation responses that explicitly present confidence bounds, retrieval score metrics, and provenance metadata in the UI/API payload.
- **Formula**:
  $$M_7 = \frac{\text{Responses Displaying Explicit Uncertainty & Provenance UI Tokens}}{\text{Total Active Consultation Responses}} \times 100\%$$
- **Target**: **100.0%**. Directly enforces Item 14 of `PILOT_ACCEPTANCE_CRITERIA.md`.

### 3.8 Therapist Override Rate ($M_8$)
- **Definition**: The frequency with which licensed therapists modify, reject, or override GraphRAG consultation suggestions during session planning.
- **Formula**:
  $$M_8 = \frac{\text{Therapist Session Overrides / Rejections}}{\text{Total Consultations Rendered}} \times 100\%$$
- **Target**: Tracked as an operational feedback baseline (< 15.0% target deviation). High override rates trigger clinical review of underlying graph relations.

### 3.9 End-to-End Latency ($M_9$)
- **Definition**: The elapsed time (in milliseconds) from initial API request receipt to final response rendering, broken down by retrieval phase.
- **Phases Tracked**:
  - `t_graph_ms`: Graph DB traversal time.
  - `t_vector_ms`: Vector embedding & search time.
  - `t_validation_ms`: Provenance & security check time.
  - `t_synthesis_ms`: Response formatting time.
- **Target**: **p95 < 2,500 ms**; hard timeout at 3,000 ms (triggers legacy fallback).

### 3.10 System Error Rate ($M_{10}$)
- **Definition**: The ratio of unhandled system exceptions or HTTP 5xx responses relative to total incoming requests.
- **Formula**:
  $$M_{10} = \frac{\text{Unhandled System Errors}}{\text{Total Requests Received}} \times 100\%$$
- **Target**: **< 0.5%**. All subsystem errors must be caught and routed through fallback orchestrators.

### 3.11 Security-Block Rate ($M_{11}$)
- **Definition**: The percentage of unauthorized access attempts, PII injection patterns, feature flag tampering attempts, or kill-switch triggers correctly identified and denied by security enforcement.
- **Formula**:
  $$M_{11} = \frac{\text{Correctly Intercepted Security Boundaries}}{\text{Total Security Violation Test Cases}} \times 100\%$$
- **Target**: **100.0%**. Enforces Gate A and Gate B compliance.

---

## 4. Operational Alignment with `PILOT_ACCEPTANCE_CRITERIA.md`

| Pilot Acceptance Criterion | Mapped Metric | Enforcement Mechanism |
| :--- | :--- | :--- |
| **Criterion 5: Zero Live Patient Data** | $M_{11}$ (Security-Block Rate) | PII Regex & Pattern Scanner in Telemetry & Security Engine |
| **Criterion 6: No Autonomous Decisions** | $M_8$ (Therapist Override Rate) | Mandatory UI Therapist Confirmation Step |
| **Criterion 8: Evidence/Uncertainty** | $M_2$ (Evidence Coverage), $M_7$ (Uncertainty Visibility) | Provenance Validator & UI Formatter |
| **Criterion 9: Master Feature Flag** | $M_{11}$ (Security-Block Rate) | Master Flag Evaluator at Gateway |
| **Criterion 10: Legacy Fallback** | $M_5$ (Fallback Success Rate) | Circuit Breaker & Fallback Orchestrator |
| **Criterion 12: Audit Trail** | $M_6$ (Audit Completeness) | Immutable Event Store & HMAC SHA256 Hash Chain |
| **Criterion 13: Safety Evaluation Passed** | $M_1$ through $M_{11}$ | 100% Pass Rate on 120 Synthetic Test Matrix Cases |

---

## 5. Synthetic Evaluation Baseline

All baseline metric validations are computed against the 120 synthetic cases in `tests/fixtures/integration_design/integration_cases.jsonl`:

- **Legacy-Only Cases (`SYN-LEG-001` to `020`)**: Verified for legacy engine response structure and zero GraphRAG invocation.
- **Shadow Comparison Cases (`SYN-SHD-001` to `020`)**: Baseline retrieval agreement ($M_1 \ge 85\%$) verified without user-facing output.
- **Reviewed Consultation Cases (`SYN-REV-001` to `020`)**: 100% evidence coverage ($M_2$) and uncertainty visibility ($M_7$) verified.
- **Blocked Novelty Cases (`SYN-NOV-001` to `020`)**: 100% novelty block rate ($M_4$) verified; unreviewed relations intercepted.
- **Fallback / Error Cases (`SYN-ERR-001` to `020`)**: 100% fallback success rate ($M_5$) verified across simulated hardware and network faults.
- **Security / Governance Cases (`SYN-SEC-001` to `020`)**: 100% security block rate ($M_{11}$) verified; all violations denied and audited.
