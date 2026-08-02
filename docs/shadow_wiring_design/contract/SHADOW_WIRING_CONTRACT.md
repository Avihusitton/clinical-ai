# Shadow Wiring Contract Specification

**Contract Version**: `1.0.1`  
**Operating Mode**: `SHADOW_COMPARE`  
**Execution Strategy**: `OFF_CRITICAL_PATH_SHADOW`  
**Core Invariant**: The user-visible response returned by `retrieval.py` must ALWAYS remain the unmutated legacy response.

---

## 1. Latency Semantics (`OFF_CRITICAL_PATH_SHADOW`)

To resolve any latency contradiction, Shadow comparison is executed strictly **off the critical path**:

1. **Execute Legacy Path**: Run standard legacy graph traversal and LLM composition.
2. **Preserve Exact Legacy Result**: Hold the resulting string in `legacy_response`.
3. **Return Immediately**: Return `legacy_response` to the caller without waiting for Shadow completion. No intentional blocking on Shadow execution is permitted; only bounded local submission overhead is allowed.
4. **Submit Redacted Shadow Task**: Submit a redacted Shadow task to an isolated bounded thread pool or local queue.
5. **Queue Saturation (`DROP_SHADOW_TASK_AND_AUDIT`)**: If the bounded queue is full or submission fails, drop the Shadow task immediately and record a `SHADOW_QUEUE_SATURATED` audit event. Never retry on the user request thread.
6. **Zero Visibility**: Shadow outputs, novelty candidates, and consultation objects are NEVER exposed to the therapist or returned in the response.
7. **Zero Raw Persistence**: Raw request narratives are scrubbed and never stored.
8. **CLI Process-Shutdown Behavior**: For CLI executions (`main()`), any pending background shadow task is given a strict bounded join timeout (e.g. 50ms) upon process exit to allow log flushing before immediate termination.

---

## 2. 10-Step Shadow Lifecycle Execution Flow

1. Receive Legacy Request
2. Execute Legacy Path
3. Preserve Legacy Result
4. Check Shadow Feature Flag (Skip if not `SHADOW_COMPARE` or emergency kill active)
5. Build Redacted Shadow Input (Sanitize Israeli PII, hash user ID)
6. Return Original Legacy Result Immediately (`OFF_CRITICAL_PATH_SHADOW`)
7. Submit Bounded Background Task
8. Execute Isolated Controlled Integration
9. Compare Outputs & Classify Difference
10. Record Redacted Metrics & Discard Shadow Payload

---

## 3. Difference Classification Matrix

| Classification Code | Description | Action Taken |
| :--- | :--- | :--- |
| `AGREEMENT` | Legacy and Shadow produced identical evidence and concept chains | Log agreement metric |
| `LEGACY_ONLY_EVIDENCE` | Evidence concept present in legacy but omitted in GraphRAG shadow | Track recall delta |
| `SHADOW_ONLY_REVIEWED_EVIDENCE` | Reviewed official evidence present in shadow but absent in legacy | Track precision expansion |
| `RANKING_DIFFERENCE` | Same evidence concepts retrieved, but ranked in different order | Track ordering variance |
| `UNCERTAINTY_DIFFERENCE` | Shadow flagged explicit clinical uncertainty missing in legacy | Track safety disclosure |
| `SAFETY_BLOCK_DIFFERENCE` | Shadow triggered safety boundary block or PII rejection | Log safety divergence |
| `FALLBACK_TRIGGERED` | Controlled integration caught error and fell back to legacy baseline | Log fallback rule |
| `SHADOW_ERROR` | Exception raised during shadow execution | Suppress error & log telemetry |
| `SHADOW_TIMEOUT` | Shadow execution exceeded latency budget | Cancel shadow task & log timeout |
