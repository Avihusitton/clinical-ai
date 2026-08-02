# Shadow Wiring Frozen Acceptance Criteria

```yaml
default_mode: LEGACY_ONLY
shadow_default_enabled: false
user_visible_shadow_output: false
protected_files_modified: 0
production_wiring_started: false
live_patient_data_used: false
status: FROZEN_FOR_SHADOW_WIRING_IMPLEMENTATION
execution_strategy: OFF_CRITICAL_PATH_SHADOW
queue_saturation_policy: DROP_SHADOW_TASK_AND_AUDIT
implementation_authorized: true
fixture_count: 140
```

## Summary of Acceptance Criteria

1. **Seam Location**: Seam `SEAM-001-ANSWER-WRAPPER` in `retrieval.py:Retriever.answer` (lines 93-109) is designated as the sole authorized integration seam.
2. **User-Visible Invariance**: Primary execution returns legacy retrieval output unmutated under all operating conditions without waiting for Shadow execution.
3. **Shadow Isolation**: Controlled integration package runs asynchronously off the critical path (`OFF_CRITICAL_PATH_SHADOW`).
4. **Queue Saturation Policy**: Under heavy load or full queues, shadow execution is dropped cleanly (`DROP_SHADOW_TASK_AND_AUDIT`) with zero exception bubbling to the caller.
5. **Fixture Validation**: 140 synthetic cases (including 20 Israeli PII security cases) cover all 7 operating domains cleanly.
6. **Emergency Disable**: Multi-channel kill-switches immediately degrade shadow comparison to `LEGACY_ONLY`.
