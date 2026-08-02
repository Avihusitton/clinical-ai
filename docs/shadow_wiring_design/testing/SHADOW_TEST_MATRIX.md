# Shadow Wiring Test Matrix

**Document Status**: `DESIGN_ONLY`  
**Total Target Fixtures**: 140 Synthetic Test Cases  
**Execution Strategy**: `OFF_CRITICAL_PATH_SHADOW`  

---

## 1. Test Domain Breakdown (20 Cases Each)

| Domain ID | Focus Area | Case ID Range | Key Assertion / Verification Goal |
| :--- | :--- | :--- | :--- |
| **DOM-01** | `shadow_disabled` | `SHD-DIS-001` .. `SHD-DIS-020` | Operating mode `LEGACY_ONLY`. Shadow comparison is completely bypassed; legacy output returned. |
| **DOM-02** | `agreement` | `SHD-AGR-001` .. `SHD-AGR-020` | Legacy and Shadow yield identical concept matches. Classify as `AGREEMENT`. |
| **DOM-03** | `controlled_difference` | `SHD-DIF-001` .. `SHD-DIF-020` | Shadow retrieves additional reviewed evidence or flags uncertainty. Classify as `SHADOW_ONLY_REVIEWED_EVIDENCE` or `UNCERTAINTY_DIFFERENCE`. |
| **DOM-04** | `failure_and_timeout` | `SHD-ERR-001` .. `SHD-ERR-020` | Shadow raises exception or times out. Assert shadow error is suppressed and legacy output returned (`SHADOW_ERROR` / `SHADOW_TIMEOUT`). |
| **DOM-05** | `security_and_redaction` | `SHD-SEC-001` .. `SHD-SEC-020` | Input contains synthetic generic PII. Verify PII rejection, telemetry redaction, zero raw storage. |
| **DOM-06** | `rollback_and_emergency` | `SHD-EMG-001` .. `SHD-EMG-020` | `EMERGENCY_DISABLED` env var or sentinel file active. Verify instant fallback to `LEGACY_ONLY` mode. |
| **DOM-07** | `israeli_pii_security` | `SHD-ISR-001` .. `SHD-ISR-020` | Synthetic Israeli context PII (ID numbers, 05x/0x/972 phones, HMO IDs, case files, street address, DOB, mixed Heb/Eng). Verify PII rejection & redaction. |

---

## 2. Mandatory Test Coverage

1. **Object Identity & Value Equality**: The exact `str` object (or equivalent value) returned by legacy `Retriever.answer` must be returned to caller.
2. **Off-Critical Path Non-Blocking**: Legacy response is returned immediately without waiting for shadow background task execution.
3. **Queue Saturation (`DROP_SHADOW_TASK_AND_AUDIT`)**: Under queue overflow, shadow task is dropped without raising exceptions or blocking caller thread.
4. **Israeli PII Scrubbing**: Complete detection and redaction of 20 synthetic Israeli quasi-identifiers.
