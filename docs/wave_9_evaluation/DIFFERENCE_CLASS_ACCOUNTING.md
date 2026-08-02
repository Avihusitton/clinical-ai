# Difference Class Accounting Report — Wave 9.1

## Overview

In Wave 9.1, difference-class taxonomy was strictly refactored to separate domain concepts:
- **`fixture_domain`**: `shadow_disabled`, `agreement`, `controlled_difference`, `failure_and_timeout`, `security_and_redaction`, `rollback_and_emergency`, `israeli_pii`
- **`operating_mode`**: `LEGACY_ONLY`, `SHADOW_COMPARE`, `EMERGENCY_DISABLED`, `UNKNOWN_MODE`
- **`submission_decision`**: `SUBMITTED`, `REJECTED_PII`, `REJECTED_EMERGENCY`, `SKIPPED_MODE`
- **`safety_decision`**: `PASS_CLEAN`, `REJECTED_ISRAELI_PII`
- **`execution_outcome`**: `COMPLETED`, `SKIPPED`, `EMERGENCY_BLOCKED`
- **`difference_class`**: Frozen contract enum values only (`AGREEMENT`, `SAFETY_BLOCK_DIFFERENCE`, `FALLBACK_TRIGGERED`, etc.)

## Frozen Contract Difference Class Accounting

```text
non_contract_labels_found: 0
```

### Observed Contract Classes
- `AGREEMENT`: 100 cases (matching synthetic legacy and shadow output fingerprints)
- `SAFETY_BLOCK_DIFFERENCE`: 20 cases (Israeli PII rejected by redaction engine)
- `FALLBACK_TRIGGERED`: 20 cases (failure & timeout synthetic cases)

### Unreachable Contract Classes (Synthetic Adapter Limitations)
- `LEGACY_ONLY_EVIDENCE`
- `SHADOW_ONLY_REVIEWED_EVIDENCE`
- `RANKING_DIFFERENCE`
- `UNCERTAINTY_DIFFERENCE`
- `SHADOW_ERROR`
- `SHADOW_TIMEOUT`

*These classes remain unreachable in Wave 9 because synthetic adapters operate offline without live LLM calls or live Neo4j evidence retrieval.*
