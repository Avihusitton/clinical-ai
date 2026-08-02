# Wave 7 Shadow Wiring Design Report (Corrected)

```yaml
AGENT_1_STATUS: COMPLETE
AGENT_2_STATUS: COMPLETE
AGENT_3_STATUS: COMPLETE
AGENT_4_STATUS: COMPLETE
DEFAULT_MODE: LEGACY_ONLY
SHADOW_DEFAULT_ENABLED: false
USER_VISIBLE_SHADOW_OUTPUT: false
EXECUTION_STRATEGY: OFF_CRITICAL_PATH_SHADOW
QUEUE_SATURATION_POLICY: DROP_SHADOW_TASK_AND_AUDIT
PROTECTED_FILES_MODIFIED: 0
PRODUCTION_WIRING_STARTED: false
LIVE_PATIENT_DATA_USED: false
FIXTURE_COUNT: 140
OLD_REPORTED_SHA256: 40a536aadd8436ca29b4bf5bc7ac226deb1eefd685146011d3aaae83028f58d2
NEW_CANONICAL_SHA256: 5df950e8459eb7b6fd34d705cc0af06fbe7b3f58ac7d8a7ab05bcba4d7277342
STATUS: PASS_WITH_REQUIRED_PREIMPLEMENTATION_CORRECTIONS
IMPLEMENTATION_AUTHORIZED: true
```

## 1. Executive Summary

Wave 7 design has been corrected to resolve latency semantics (`OFF_CRITICAL_PATH_SHADOW`), define queue-saturation rules (`DROP_SHADOW_TASK_AND_AUDIT`), add 20 synthetic Israeli PII test cases (totaling 140 fixtures), and recompute the canonical combined SHA256 manifest digest (`5df950e8459eb7b6fd34d705cc0af06fbe7b3f58ac7d8a7ab05bcba4d7277342`).

## 2. Key Design Corrections

1. **Seam Selection**: `SEAM-001-ANSWER-WRAPPER` (`Retriever.answer`, lines 93-109) confirmed as sole integration seam.
2. **Latency Semantics**: `OFF_CRITICAL_PATH_SHADOW`. Primary legacy response returned immediately without waiting for Shadow execution.
3. **Queue Saturation**: Under full queues, tasks are dropped cleanly (`DROP_SHADOW_TASK_AND_AUDIT`) without retrying on request thread.
4. **140 Fixture Dataset**: Expanded to 140 cases including 20 synthetic Israeli context quasi-identifiers.
