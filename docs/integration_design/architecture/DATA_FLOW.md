# Controlled Integration Data Flow Specification

## 1. Request Data Flow Architecture

The request data flow governs how incoming user queries are wrapped into an `IntegrationRequest`, evaluated against active feature flags and operating modes, routed through gate adapters, and returned as a structured `IntegrationDecision` and `IntegrationExplanation`.

```mermaid
graph TD
    A[Client Request / Query] --> B[IntegrationRequest Instantiation]
    B --> C{FeatureFlagEvaluator}
    C -->|EMERGENCY_DISABLED| D[FallbackHandler / Legacy Retrieval]
    C -->|LEGACY_ONLY| D
    C -->|OFFICIAL_RETRIEVAL_ONLY| E[Gate B Adapter]
    C -->|THERAPIST_PILOT| F[Full Integration Pipeline]
    
    E --> G[OfficialEvidenceBundle]
    G --> H[IntegrationDecision: OFFICIAL_RAG_SERVED]
    
    F --> I[Gate B Reasoning Adapter]
    I --> J[Gate C Novelty Adapter]
    J --> K[Gate C/D Boundary Adapter]
    K --> L[ConsultationInputBundle]
    L --> M[Gate D Consultation Adapter]
    M --> N[ConsultationOutputBundle]
    N --> O[IntegrationDecision: FULL_PILOT_SERVED]
    
    D --> P[IntegrationDecision: FALLBACK_TRIGGERED / LEGACY_SERVED]
```

### Step-by-Step Request Execution Pipeline:
1. **Query Ingestion**: The entry point receives a raw query string, session context, and optional feature flag overrides, creating an immutable `IntegrationRequest`.
2. **Context & Role Validation**: `IntegrationContext` verifies user authorization (`ROLE_INTERNAL_THERAPIST` required for pilot mode).
3. **Mode & Flag Evaluation**: `FeatureFlagEvaluator` checks environment variables and config files to determine the active operating mode.
4. **Execution Dispatch**:
   - `LEGACY_ONLY`: Directly dispatches to `legacy_adapter` (`retrieval.py`).
   - `OFFICIAL_RETRIEVAL_ONLY`: Executes Gate A/B retrieval only via `gate_b_adapter`.
   - `THERAPIST_PILOT`: Executes full multi-gate pipeline via boundary screening.
   - `EMERGENCY_DISABLED` or Exception: Dispatches immediately to `FallbackHandler`.

---

## 2. Evidence Filtering & Boundary Data Flow

This flow illustrates how evidence originates from Gate B, undergoes novelty analysis in Gate C, passes through the deterministic Gate C/D boundary filter, and forms the screened `ConsultationInputBundle` for Gate D.

```mermaid
sequenceDiagram
    autonumber
    participant GB as Gate B (Reasoner)
    participant GC as Gate C (Novelty Engine)
    participant BND as Gate C/D Boundary
    participant GD as Gate D (Consultation)

    GB->>GC: Forward Accepted Traversal Paths
    GC->>GC: Process Candidates (Known Check, Duplicate Check, Contradiction Check)
    Note over GC: All candidates marked status="DISCOVERY_ONLY"<br/>review_status="PENDING_HUMAN_REVIEW"
    GC->>BND: Submit NoveltyCandidates & EvidenceBundles
    GB->>BND: Submit Approved ReviewedEvidenceProviders
    
    rect rgb(240, 240, 240)
        Note over BND: Boundary Screening (EvidenceEligibilityChecker)
        BND->>BND: Reject DISCOVERY_ONLY candidates
        BND->>BND: Reject PENDING_HUMAN_REVIEW candidates
        BND->>BND: Reject POSSIBLE_CONTRADICTION candidates
        BND->>BND: Reject INSUFFICIENT_EVIDENCE candidates
        BND->>BND: Allow ONLY is_approved=True & is_reviewed=True
    end
    
    BND->>GD: Deliver ConsultationInputBundle (Eligible Official Evidence ONLY)
    Note over GD: Gate D consumes zero unreviewed Gate C novelty
    GD-->>BND: ConsultationResponse (Possibilities, Boundaries, Uncertainties)
```

### Detailed Boundary Rules:
- **Input to Boundary**: Raw Gate B traversal paths and raw Gate C novelty candidates.
- **Evaluation**: `EvidenceEligibilityChecker` evaluates every item without mutating any object.
- **Filtering Verdicts**:
  - `ReviewedEvidenceProvider` (Approved=True, Reviewed=True) -> `ELIGIBLE`.
  - `NoveltyEvidenceFilter` (Status=DISCOVERY_ONLY) -> `BLOCKED` (`BlockedReason.DISCOVERY_ONLY`).
  - `NoveltyEvidenceFilter` (ReviewStatus=PENDING_HUMAN_REVIEW) -> `BLOCKED` (`BlockedReason.PENDING_HUMAN_REVIEW`).
  - `NoveltyEvidenceFilter` (Type=POSSIBLE_CONTRADICTION) -> `BLOCKED` (`BlockedReason.UNRESOLVED_CONTRADICTION`).
- **Output**: `ConsultationInputBundle` containing *only* items with verdict `ELIGIBLE`. `blocked_count` is incremented for all blocked items.

---

## 3. Error & Fallback Data Flow

When a boundary violation, unhandled exception, or invalid flag combination occurs, the error pipeline isolates the failure and executes a fail-closed fallback to legacy retrieval.

```mermaid
graph TD
    A[Error / Exception Occurs in Gate B/C/D or Boundary] --> B[IntegrationException Captured]
    B --> C{Is Unreviewed Novelty Leak or Boundary Violation?}
    C -->|Yes| D[Log CRITICAL Security Alarm]
    C -->|No| E[Log ERROR Event]
    
    D --> F[Open Circuit Breaker]
    E --> F
    
    F --> G[FallbackHandler Invocation]
    G --> H[Execute Legacy Retrieval: retrieval.py]
    H --> I[Legacy Response Returned]
    I --> J[Wrap in IntegrationDecision: FALLBACK_TRIGGERED]
    J --> K[Return Fallback to Client]
```

### Key Safety Invariants in Error Flow:
1. **Zero Downtime**: The end user always receives a response (either legacy baseline or fallback), even if advanced RAG fails.
2. **Zero Unsafe Output**: An error in Gate C or D never leads to unvalidated output being served; fallback to legacy baseline is instant.
3. **Audit Trail**: Every fallback invocation writes an immutable audit record containing error stack trace, session ID, and timestamp.

---

## 4. Audit & Telemetry Data Flow

All pipeline operations emit non-blocking, structured audit events and performance metrics.

```mermaid
graph LR
    Subsystems[Pipeline Subsystems] -->|Emit Event| Logger[AuditLogger]
    Logger --> Redactor[PII / PHI Redactor]
    Redactor --> JSONStream[JSON Audit Log Stream]
    
    Subsystems -->|Emit Metrics| Telemetry[TelemetryCollector]
    Telemetry --> Aggregator[Latency & Count Aggregator]
    Aggregator --> MetricsSummary[Integration Metrics Summary]
```

### Log & Telemetry Fields:
- **Audit Logs**: `event_id`, `event_type`, `request_id`, `session_id`, `details` (sanitized query, decision, blocking reasons), `timestamp`.
- **Telemetry Metrics**: `request_latency_ms`, `gate_b_latency_ms`, `gate_c_latency_ms`, `boundary_latency_ms`, `gate_d_latency_ms`, `total_evidence_evaluated`, `eligible_evidence_count`, `blocked_evidence_count`, `fallback_trigger_count`.
