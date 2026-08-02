# Relation Policy Draft

* **Unknown-Relation Rejection**: Enforced via a strict whitelist (`cfg.reasoning_relationship_types`) in Cypher graph traversals (`retrieval.py`).
* **Cycle Rejection**: UNKNOWN.
* **Self-loop Rejection**: UNKNOWN.

* **Exercise Bridge Blocking**:
CURRENT_LEGACY_BEHAVIOR:
Exercise may appear as an intermediate node. This is a documented legacy defect.

PROPOSED_GATE_B_BEHAVIOR:
Exercise is terminal and may never act as an inferential bridge.

* **No Permanent Inferred Graph Writes**: Confirmed. Retrieval operations run read-only `MATCH` queries without creating inferred edges. This is enforced by test `test_guard_no_live_mutations`.
