# Automated & Manual Shutdown Triggers Specification

## 1. Overview & Emergency Governance

This specification defines the automated safety alarms, manual emergency disable controls, and automated kill-switch triggers for the Clinical AI platform. 

The core safety imperative is: **When in doubt, freeze the system**. If any automated monitoring probe detects a clinical safety violation, data privacy breach, audit logging failure, or latency breach, the platform instantly transitions to `EMERGENCY_DISABLED` mode without waiting for human intervention.

---

## 2. Automated Shutdown Triggers Catalog (P0 Alarms)

The system actively evaluates 6 automated P0 shutdown triggers during runtime.

| Trigger ID | Trigger Name | Threshold / Condition | Evaluation Window | Automated Action | Severity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **TRIG-P0-01** | **Hallucination / Ungrounded Statement Rate** | > 0.0% ungrounded assertions in audit sample. | Real-time / Per query | Instant transition to `EMERGENCY_DISABLED`. Page Clinical Safety Officer. | **CRITICAL** |
| **TRIG-P0-02** | **Evidence Provenance Missing Rate** | > 0% of RAG queries returning chunks without verifiable document ID & content hash. | Real-time / Per query | Revert operating mode to `LEGACY_ONLY`. Freeze GraphRAG pipeline. | **CRITICAL** |
| **TRIG-P0-03** | **Live Patient Data / PII Detection** | > 0 occurrences of real patient identifiers (national ID, full names, phone numbers) in prompt or response. | Real-time regex & NER scanner | Instant transition to `EMERGENCY_DISABLED`. Purge transient cache. Alert Security Lead. | **FATAL** |
| **TRIG-P0-04** | **Audit Logging Service Failure** | Failure to commit trace record to audit log (disk full, DB write error, logger exception). | Real-time / Pre-response commit | Instant transition to `EMERGENCY_DISABLED`. Block all response egress. | **CRITICAL** |
| **TRIG-P0-05** | **Consecutive Error Spike** | > 3 unhandled pipeline errors within a rolling 5-minute window. | Rolling 5-minute window | Transition operating mode to `LEGACY_ONLY`. Disable GraphRAG flags. | **HIGH** |
| **TRIG-P0-06** | **Latency Threshold Breach** | p99 response time > 5000ms OR Neo4j graph traversal timeout > 2000ms over 5 consecutive queries. | Rolling 10-query window | Degrade to `OFFICIAL_RETRIEVAL_ONLY` or `LEGACY_ONLY`. | **HIGH** |

---

## 3. Automated Monitoring & Detection Probes

The automated kill-switch engine relies on four background detection probes:

```
┌────────────────────────────────────────────────────────────────┐
│                   Automated Safety Sentinel                    │
└───────┬──────────────────┬──────────────────┬──────────────────┘
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│  PII & Data  │   │  Provenance  │   │ Audit Logger │
│ Privacy Probe│   │ Integrity    │   │ Health       │
│  (TRIG-03)   │   │  (TRIG-02)   │   │  (TRIG-04)   │
└───────┬──────┘   └───────┬──────┘   └───────┬──────┘
        │                  │                  │
        └──────────────────┼──────────────────┘
                           │
                           ▼ (Violation Detected)
            ┌─────────────────────────────┐
            │  TRIGGER KILL-SWITCH        │
            │  Mode -> EMERGENCY_DISABLED │
            └─────────────────────────────┘
```

1. **Data Privacy Probe (PII Scanner)**:
   Scans incoming query text and outgoing model responses against Israeli ID patterns, phone number formats (`05x`, `972`), e-PHI patterns, and real patient names. If detected, fires **TRIG-P0-03**.

2. **Provenance Integrity Scanner**:
   Validates every retrieved chunk before passing to LLM synthesis. Ensures `doc_type`, `heading_anchor`, and `content_hash` exist in `data/content_hashes.json`. If missing, fires **TRIG-P0-02**.

3. **Audit Logger Health Checker**:
   Executes a heart-beat test prior to processing each request. Verifies that the audit log file system / table is writable and synched. If write fails, fires **TRIG-P0-04**.

4. **Error Rate & Latency Monitor**:
   Tracks rolling query error counts and p99 response latencies. If thresholds are exceeded, fires **TRIG-P0-05** or **TRIG-P0-06**.

---

## 4. Manual Shutdown & Emergency Disable Controls

In addition to automated probes, authorized personnel can trigger an immediate manual shutdown using any of the following four mechanisms:

### Method A: Environment Variable Hot Override
Set the environment variable on the server or application container:
```bash
export CLINICAL_AI_EMERGENCY_DISABLE=true
```
The application detects this variable within **< 50ms** on the next request cycle and forces `operating_mode = EMERGENCY_DISABLED`.

### Method B: Physical Emergency Kill-Switch File
Create an empty sentinel file in the workspace data directory:
```bash
touch data/EMERGENCY_DISABLE.sentinel
```
The application watcher detects file creation instantly and triggers shutdown.

### Method C: Admin Emergency REST API Endpoint
Send an authenticated HTTP POST request to the management endpoint:
```http
POST /api/v1/control/emergency-disable
Header: X-Admin-Emergency-Key: <SECURE_EMERGENCY_TOKEN>
Content-Type: application/json

{
  "reason": "Observed abnormal graph reasoning outputs during pilot session",
  "operator": "cso_oncall_user"
}
```

### Method D: Command-Line Interface (CLI) Override
Execute the local control script:
```bash
python scripts/control_cli.py --mode EMERGENCY_DISABLED --reason "Manual override by CSO"
```

---

## 5. Immediate Action Sequence Upon Trigger Activation

When a shutdown trigger (automated or manual) is activated, the application executes the following deterministic 5-step emergency sequence:

```
[ Trigger Fired ] ──► Step 1: Mode -> EMERGENCY_DISABLED
                  ──► Step 2: Revoke Active Pilot Sessions
                  ──► Step 3: Freeze Vector/Graph Queries
                  ──► Step 4: Flush Audit Buffer & Log P0 Event
                  ──► Step 5: Dispatch PagerDuty / Email Alert
```

1. **Step 1 (State Flip)**: Set `operating_mode = EMERGENCY_DISABLED` and set all feature flags to `false` in memory.
2. **Step 2 (Session Revocation)**: Invalidate active therapist pilot tokens (`therapist_pilot_access_enabled = false`). Divert all new requests to deterministic static fallback.
3. **Step 3 (Resource Freeze)**: Terminate active OpenRouter LLM requests and Neo4j graph traversal jobs.
4. **Step 4 (Audit Flush)**: Flush pending audit log buffers to disk with `EVENT_EMERGENCY_KILLSWITCH_ACTIVE` including trigger metadata and timestamp.
5. **Step 5 (Alerting)**: Dispatch P0 high-priority alerts to On-Call Engineers, Clinical Safety Officer, and Lead Architect.

---

## 6. System Resumption & Re-activation Criteria

Once the system has entered `EMERGENCY_DISABLED` mode, it **CANNOT** automatically self-heal or return to `THERAPIST_PILOT` mode.

Re-activation requires completing the following formal recovery checklist:

1. **Root Cause Analysis (RCA)**: Documented RCA signed off by Lead Architect and Security Lead.
2. **Resolution & Patch Verification**: Code or configuration fix deployed and verified in `DEV` and `STAGING`.
3. **Audit File Clear**: Removal of `data/EMERGENCY_DISABLE.sentinel` and reset of `CLINICAL_AI_EMERGENCY_DISABLE=false`.
4. **Formal Sign-off**: Dual sign-off from:
   - Clinical Safety Officer
   - Chief Technology Officer / Lead Architect
5. **Graduated Re-activation**:
   - Step A: Restore to `LEGACY_ONLY` for 15 minutes.
   - Step B: Restore to `SHADOW_COMPARE` for 30 minutes (verify zero diff anomalies).
   - Step C: Restore to `THERAPIST_PILOT` mode.
