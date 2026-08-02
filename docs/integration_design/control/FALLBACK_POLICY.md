# Fallback Policy & Graceful Degradation Framework

## 1. Governance & Operational Philosophy

The Clinical AI platform operates under a strict **Fail Closed & Graceful Degradation Policy**. In a clinical decision-support domain, serving an unverified, hallucinated, or ungrounded generative response is unacceptable. 

If any component of the GraphRAG pipeline encounters a failure, ambiguity, missing evidence provenance, or configuration anomaly, the system MUST gracefully degrade to a safe, deterministic operational tier or immediately revert to the legacy baseline response.

---

## 2. Mandatory Fallback Rules

The framework defines four core mandatory fallback rules:

```
[ Incoming User Query ]
          │
          ├──► System / Network / LLM Failure ─────► [ RULE 1: Legacy Baseline Response ]
          │
          ├──► Gate C Novelty Discovery Failure ───► [ RULE 2: Standard RAG (No Novelty) ]
          │
          ├──► Gate D Consultation Format Fail ────► [ RULE 3: Raw Evidence Chunks (No Autonomous Advice) ]
          │
          └──► Missing Provenance / Unknown Flag ──► [ RULE 4: Immediate Fail Closed to Legacy ]
```

### Rule 1: General Failure Fallback (`Any Failure -> Legacy Response`)
* **Trigger Conditions**: Unhandled API exceptions, OpenRouter LLM timeouts (> 5000ms), Neo4j connection failure, vector store unavailability, or invalid response payload formatting.
* **System Action**: Immediately abort RAG pipeline processing. Divert query execution to the legacy baseline retrieval system.
* **Output Standard**: Pure legacy baseline answer.
* **User Notification**: None shown to end user (seamless fallback). System audit log records `EVENT_PIPELINE_FALLBACK` with full exception trace.

### Rule 2: Gate C Novelty Fallback (`Gate C Fail -> No Novelty`)
* **Trigger Conditions**: Gate C hypothesis confidence score < 0.85, unverified cross-domain relationship, missing literature validation node, or `gate_c_novelty_enabled == false`.
* **System Action**: Suppress all novel therapeutic relation claims and multi-hop speculative inferences. Fall back to standard, verified GraphRAG retrieval output.
* **Output Standard**: Standard RAG response containing only explicit, directly linked nodes from `glossary.json` and official methodology documents.
* **Payload Attribute**: `novelty_suppressed: true`, `novelty_reason: "GATE_C_CONFIDENCE_BELOW_THRESHOLD"`.

### Rule 3: Gate D Advisory Fallback (`Gate D Fail -> No Autonomous Advice`)
* **Trigger Conditions**: Gate D formatting template engine error, advice boundary threshold trigger (e.g., query touches high-risk clinical triage), or `gate_d_formatting_enabled == false`.
* **System Action**: Suppress all generative consultation formatting and synthesized advisory recommendations.
* **Output Standard**: Return raw retrieved evidence chunks and document excerpts with an explicit clinical disclaimer:
  > *"Advisory formatting unavailable. Presenting verified source evidence chunks for human therapist review."*
* **Payload Attribute**: `autonomous_advice_suppressed: true`, `output_type: "RAW_EVIDENCE_ONLY"`.

### Rule 4: Integrity & Provenance Fallback (`Missing Evidence / Unknown Flag -> Fail Closed`)
* **Trigger Conditions**: 
  - GraphRAG query returns chunks without verifiable source provenance (missing document ID, chunk hash, or anchor reference).
  - Feature flag validator detects an unknown flag key, missing schema attribute, or corrupted JSON configuration.
  - User authorization token lacks required RBAC scope for therapist pilot access.
* **System Action**: Instantly **Fail Closed**. Block RAG processing and return legacy response.
* **Output Standard**: Pure legacy baseline answer with high-priority security audit event `EVENT_FAIL_CLOSED_TRIGGERED`.

---

## 3. Tiered Graceful Degradation Hierarchy

The table below summarizes the operational tiers and fallback transitions across all system failure modes:

| Tier | Operational Mode | Functional Capabilities | Trigger / Fallback Cause | Response Payload Type | Audit Event Logged |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 0** | Full Therapist Pilot (`THERAPIST_PILOT`) | Official retrieval, GraphRAG reasoning, Gate C novelty, Gate D consultation synthesis. | Normal operation under full pilot readiness sign-off. | Synthesized Clinical Consultation Template | `EVENT_PILOT_QUERY_SUCCESS` |
| **Tier 1** | Standard Verified RAG | Official retrieval, Gate B multi-hop reasoning, Gate D formatting. (Gate C novelty suppressed). | Gate C novelty validation failure or low confidence score. | Verified RAG Output (No Novelty) | `EVENT_GATE_C_SUPPRESSED` |
| **Tier 2** | Raw Evidence Only | Official document retrieval (Gate A/B retrieval). Generative advice & formatting suppressed. | Gate D formatting error or high-risk clinical boundary trigger. | Raw Source Chunks + Review Disclaimer | `EVENT_GATE_D_SUPPRESSED` |
| **Tier 3** | Official Retrieval Only (`OFFICIAL_RETRIEVAL_ONLY`) | Glossary lookups and exact document match excerpts. Zero LLM generation. | LLM service outage, OpenRouter rate-limiting, or `gate_b_reasoning_enabled == false`. | Deterministic Glossary & Document Excerpts | `EVENT_RETRIEVAL_ONLY_FALLBACK` |
| **Tier 4** | Legacy Baseline (`LEGACY_ONLY`) | Legacy retrieval & baseline pipeline logic. | System failure, missing provenance, invalid flag, or `CLINICAL_AI_OPERATING_MODE=LEGACY_ONLY`. | Legacy Baseline Output | `EVENT_PIPELINE_FALLBACK` |
| **Tier 5** | Emergency Static (`EMERGENCY_DISABLED`) | Static fallback error page / response. Zero database or API calls. | Emergency kill-switch trigger, audit trail logger failure, or PII leak alarm. | Deterministic Emergency Notice | `EVENT_EMERGENCY_KILLSWITCH_ACTIVE` |

---

## 4. Fallback Response Payload Schemas

When a fallback is executed, the API response object includes structured fallback metadata so frontend clients and audit monitors can render appropriate UI indicators.

### Example: Tier 2 Fallback Response (Raw Evidence Only - Gate D Fail)
```json
{
  "query_id": "q-20260722-8841",
  "status": "DEGRADED",
  "operating_mode_active": "THERAPIST_PILOT",
  "tier_executed": "TIER_2_RAW_EVIDENCE_ONLY",
  "fallback_flags": {
    "legacy_fallback_used": false,
    "novelty_suppressed": true,
    "autonomous_advice_suppressed": true,
    "fallback_reason": "GATE_D_FORMATTING_ERROR_SAFETY_TRIGGER"
  },
  "content": {
    "disclaimer": "ATTENTION: Generative consultation formatting is suppressed for safety compliance. Displaying raw verified source evidence for human clinical review.",
    "evidence_chunks": [
      {
        "chunk_id": "chk-official-method-042",
        "doc_title": "Official Therapeutic Method Guidelines v3",
        "provenance": {
          "doc_type": "OFFICIAL_METHODOLOGY",
          "heading_anchor": "Section 4.2: Anxiety Exposure Protocols",
          "content_hash": "a8f9c4..."
        },
        "text": "..."
      }
    ]
  },
  "audit_trace_id": "trace-8841-gate-d-fail"
}
```

### Example: Tier 4 Fallback Response (Legacy Baseline - Rule 1 / Rule 4)
```json
{
  "query_id": "q-20260722-8842",
  "status": "FALLBACK_LEGACY",
  "operating_mode_active": "LEGACY_ONLY",
  "tier_executed": "TIER_4_LEGACY_BASELINE",
  "fallback_flags": {
    "legacy_fallback_used": true,
    "novelty_suppressed": true,
    "autonomous_advice_suppressed": true,
    "fallback_reason": "PROVENANCE_MISSING_FAIL_CLOSED"
  },
  "content": {
    "text": "[Legacy system output response content...]"
  },
  "audit_trace_id": "trace-8842-legacy-fallback"
}
```

---

## 5. Audit Logging for Fallback Events

All fallback triggers MUST generate an immutable audit log entry containing:
1. `timestamp_utc`: ISO 8601 UTC timestamp.
2. `query_id`: Unique correlation ID.
3. `trigger_rule`: `RULE_1_SYSTEM_FAIL`, `RULE_2_GATE_C_FAIL`, `RULE_3_GATE_D_FAIL`, or `RULE_4_FAIL_CLOSED`.
4. `exception_class`: Exception name or validation error code.
5. `stack_trace_snippet`: Truncated sanitized stack trace (no PII/patient data).
6. `target_fallback_tier`: Tier index (1 to 5).
