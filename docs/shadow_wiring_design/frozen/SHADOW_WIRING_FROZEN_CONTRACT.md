# Shadow Wiring Frozen Contract Specification

**Contract Version**: `1.0.1`  
**Status**: `FROZEN_FOR_SHADOW_WIRING_IMPLEMENTATION`  
**Execution Strategy**: `OFF_CRITICAL_PATH_SHADOW`  
**Implementation Authorized**: `true`  

---

## Immutable System Invariants

1. **Default Mode**: `LEGACY_ONLY`
2. **Shadow Default Enabled**: `false`
3. **User-Visible Shadow Output**: `false` (Legacy output returned 100% of the time without waiting for Shadow)
4. **Protected Baseline Modifications**: `0`
5. **Production Wiring Started**: `false`
6. **Live Patient Data Used**: `false`
7. **External Network / LLM Calls in Adapter Layer**: `0`
8. **Neo4j Graph Mutations**: `0`
9. **Total Fixtures Tracked**: `140` (includes 20 Israeli PII security cases)
10. **Queue Saturation Policy**: `DROP_SHADOW_TASK_AND_AUDIT`

---

## Contract Approval Checklist

- [x] All JSON and JSONL files parse validly.
- [x] Synthetic fixture count is exactly 140 cases (including 20 Israeli PII cases).
- [x] Legacy response is preserved under all conditions off the critical response path.
- [x] Shadow execution is disabled by default.
- [x] Shadow error/timeout failure does not interrupt legacy execution.
- [x] Emergency disable overrides shadow mode.
- [x] Unreviewed novelty candidates cannot reach the legacy response.
- [x] Telemetry data redacts PII (including Israeli quasi-identifiers) and hashes user IDs.
- [x] Zero production code modified in Wave 7 design corrections.
