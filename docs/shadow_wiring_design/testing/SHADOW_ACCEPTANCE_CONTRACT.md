# Shadow Acceptance Contract

**Contract Version**: `1.0.1`  
**Execution Strategy**: `OFF_CRITICAL_PATH_SHADOW`  
**Scope**: Acceptance criteria for future isolated shadow wiring implementation.

---

## Acceptance Requirements

1. **140 Fixture Assertion**: All 140 synthetic cases in `tests/fixtures/shadow_wiring/shadow_cases.jsonl` (including 20 Israeli PII security cases) must be executed and asserted cleanly in the test suite.
2. **User-Visible Invariance**: For 100% of test cases, `expected_user_visible_result == legacy_result`. Legacy response is returned immediately without waiting for shadow background execution.
3. **Queue Saturation Policy**: Under heavy load or full queues, shadow execution is dropped cleanly (`DROP_SHADOW_TASK_AND_AUDIT`) with zero exception bubbling to the caller.
4. **Israeli PII Redaction**: All 20 synthetic Israeli PII cases (ID numbers, 05x/0x/972 phones, HMO IDs, case files, mixed Heb/Eng) trigger PII detection, telemetry redaction, and audit logging.
5. **Zero Write Verification**: AST tests must verify zero graph writes, zero Neo4j mutations, zero network requests, and zero LLM API calls during shadow execution.
6. **Audit & Telemetry Integrity**: All audit entries must maintain SHA-256 hash chaining, and all telemetry records must hash therapist IDs.
