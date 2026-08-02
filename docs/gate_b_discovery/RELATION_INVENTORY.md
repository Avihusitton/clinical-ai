# Relation Inventory

## Inferential Relations (Concept to Concept)
* **`IS_SYMPTOM_OF`**: Directed.
* **`LEADS_TO`**: Directed. Contradictions: UNKNOWN.
* **`PREVENTS`**: Directed. Contradictions: UNKNOWN.
* **`IS_RECOMMENDED_FOR`**: Directed. Contradictions: UNKNOWN.
* **`IS_CONTRAINDICATED_FOR`**: Directed. Contradictions: UNKNOWN.

## Terminal Relations
* **`WORKS_ON`**: Directed from `Exercise` to `Concept`.

## Navigation-Only Relations
* **`HAS_CANDIDATE`**: Directed from `Chunk` to `Concept`/`Exercise` (pre-LLM match).
* **`LINKED_TO`**: Directed from `Chunk` to `Concept`/`Exercise` (post-LLM validation).

## Additional Properties
* **Symmetric and Inverse Behavior**: UNKNOWN.
* **Contradictions**: UNKNOWN (explicit repository evidence does not support specific contradictory pairs).

## Exercise Role
CURRENT_LEGACY_BEHAVIOR:
Exercise may appear as an intermediate node. This is a documented legacy defect.

PROPOSED_GATE_B_BEHAVIOR:
Exercise is terminal and may never act as an inferential bridge.
