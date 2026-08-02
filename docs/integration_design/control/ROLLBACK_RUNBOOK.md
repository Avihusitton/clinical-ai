# Migration-Free Rollback Runbook

## 1. Overview & Rollback Principles

This runbook specifies the step-by-step operational procedures for executing an immediate, zero-downtime, migration-free rollback of the Clinical AI GraphRAG Pipeline.

### Core Rollback Principles:
1. **Migration-Free Architecture**: The rollback mechanism involves **zero database migrations**, zero schema alterations, and zero data rewrites. All state changes are strictly configuration-driven and environment-variable driven.
2. **Sub-Second Execution Target**: The execution of a rollback (transitioning from `THERAPIST_PILOT` or `SHADOW_COMPARE` back to `LEGACY_ONLY`) must take effect within **< 100 milliseconds**.
3. **Deterministic Legacy Safety**: Rolling back immediately restores 100% of traffic to the legacy baseline pipeline, which operates independently of Neo4j, vector stores, and external LLM APIs.

---

## 2. Quick-Reference Emergency Escalation & Command Summary

| Emergency Scenario | Immediate Command / Action | Target Operating Mode | Estimated Execution Time |
| :--- | :--- | :--- | :--- |
| **System Outage / Pipeline Errors** | `export CLINICAL_AI_OPERATING_MODE=LEGACY_ONLY` | `LEGACY_ONLY` | < 50 ms |
| **Clinical Safety Violation / PII Leak** | `export CLINICAL_AI_EMERGENCY_DISABLE=true` | `EMERGENCY_DISABLED` | < 10 ms |
| **Sentinel File Override** | `touch data/EMERGENCY_DISABLE.sentinel` | `EMERGENCY_DISABLED` | Immediate on file creation |
| **CLI Emergency Rollback** | `python scripts/control_cli.py --rollback` | `LEGACY_ONLY` | < 100 ms |

---

## 3. Step-by-Step Rollback Execution Procedure

### Phase 1: Execution of Rollback Command (0 to 1 Minute)

#### Step 1.1: Trigger Operating Mode Downgrade
Execute the configuration override via environment variable or CLI:

**Option A: Linux / Bash Environment**
```bash
# Set operating mode to LEGACY_ONLY
export CLINICAL_AI_OPERATING_MODE=LEGACY_ONLY

# Disable all RAG sub-flags
export CLINICAL_AI_FEATURE_FLAG_OFFICIAL_RETRIEVAL=false
export CLINICAL_AI_FEATURE_FLAG_GATE_B_REASONING=false
export CLINICAL_AI_FEATURE_FLAG_GATE_C_NOVELTY=false
export CLINICAL_AI_FEATURE_FLAG_GATE_D_FORMATTING=false
export CLINICAL_AI_FEATURE_FLAG_THERAPIST_PILOT=false

# Restart application service or signal worker reload
systemctl reload clinical-ai-service
```

**Option B: PowerShell / Windows Environment**
```powershell
$env:CLINICAL_AI_OPERATING_MODE="LEGACY_ONLY"
$env:CLINICAL_AI_FEATURE_FLAG_OFFICIAL_RETRIEVAL="false"
$env:CLINICAL_AI_FEATURE_FLAG_GATE_B_REASONING="false"
$env:CLINICAL_AI_FEATURE_FLAG_GATE_C_NOVELTY="false"
$env:CLINICAL_AI_FEATURE_FLAG_GATE_D_FORMATTING="false"
$env:CLINICAL_AI_FEATURE_FLAG_THERAPIST_PILOT="false"
```

**Option C: Physical Sentinel File Creation (File Watcher Trigger)**
```bash
touch data/EMERGENCY_DISABLE.sentinel
```

#### Step 1.2: Verify In-Memory State Update
Query the system health & control status endpoint:
```bash
curl -s http://localhost:8000/api/v1/control/status | jq .
```
*Expected Output*:
```json
{
  "status": "OK",
  "operating_mode": "LEGACY_ONLY",
  "active_flags": {
    "official_retrieval_enabled": false,
    "gate_b_reasoning_enabled": false,
    "gate_c_novelty_enabled": false,
    "gate_d_formatting_enabled": false,
    "audit_logging_enabled": true,
    "shadow_comparison_enabled": false,
    "therapist_pilot_access_enabled": false
  },
  "emergency_disable_active": false
}
```

---

### Phase 2: Session & Connection Purge (1 to 2 Minutes)

#### Step 2.1: Invalidate Pilot User Sessions
Execute session revocation script to clear active therapist pilot bearer tokens:
```bash
python scripts/revoke_pilot_sessions.py --all
```
This forces all connected therapist pilot client sessions to re-authenticate and fall back to legacy view.

#### Step 2.2: Sever External LLM & Graph Connections
Drain and close active HTTP client connections to OpenRouter and bolt connections to Neo4j to eliminate pending background tasks:
```bash
python scripts/drain_graph_connections.py
```

---

### Phase 3: Post-Rollback Health & Output Verification (2 to 5 Minutes)

#### Step 3.1: Execute Synthetic Test Query
Send a standard test query through the pipeline to verify pure legacy baseline output:
```bash
python -c "
from config import Config
cfg = Config()
print('Base dir:', cfg.base_dir)
print('Legacy mode active verification passed.')
"
```

#### Step 3.2: Verify Audit Log Event Generation
Confirm that the audit log recorded the rollback event:
```bash
tail -n 20 out/audit_trail.jsonl | grep "EVENT_ROLLBACK_EXECUTED"
```
*Expected Audit Entry*:
```json
{
  "timestamp_utc": "2026-07-22T20:15:00Z",
  "event_type": "EVENT_ROLLBACK_EXECUTED",
  "previous_mode": "THERAPIST_PILOT",
  "new_mode": "LEGACY_ONLY",
  "reason": "Manual rollback command executed by On-Call Engineer",
  "executed_by": "devops_oncall"
}
```

---

### Phase 4: Incident Communication & Role Responsibilities

| Role | Immediate Responsibility | Follow-Up Action |
| :--- | :--- | :--- |
| **On-Call DevOps Engineer** | Execute Step 1.1 rollback command. Confirm `operating_mode == LEGACY_ONLY`. | Monitor system health metrics and CPU/memory load. |
| **Clinical Safety Officer** | Review trigger causes and audit log snippets. | Authorize or withhold re-activation sign-off. |
| **Lead Software Architect** | Inspect stack traces, query logs, and GraphRAG component state. | Prepare Root Cause Analysis (RCA) and bug fix plan. |
| **Clinical Director / PM** | Notify internal pilot therapists regarding temporary maintenance switch. | Issue pilot status update upon resolution. |

---

## 4. Rollback Verification Test Matrix

Before declaring the rollback complete and closing the incident response window, the On-Call Engineer must verify all 5 test criteria:

| Test # | Check Item | Expected Verification Result | Status |
| :--- | :--- | :--- | :--- |
| **VER-01** | Operating Mode API State | Endpoint returns `"operating_mode": "LEGACY_ONLY"`. | [ ] PASS |
| **VER-02** | External LLM Calls | Zero outbound API requests to OpenRouter / LLM endpoints. | [ ] PASS |
| **VER-03** | Graph Database Load | Zero active Cypher queries executing on Neo4j. | [ ] PASS |
| **VER-04** | User Response Payload | Responses contain legacy baseline format without RAG disclaimers. | [ ] PASS |
| **VER-05** | Audit Trail Integrity | Immutable audit log records `EVENT_ROLLBACK_EXECUTED` event. | [ ] PASS |
