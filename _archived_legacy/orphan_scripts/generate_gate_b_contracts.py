import hashlib
import os

os.makedirs('docs/gate_b_discovery', exist_ok=True)

f1 = """{
  "entities": {
    "RelationDefinition": {
      "description": "Defines the semantic and traversal rules for a specific relationship type in the knowledge graph.",
      "fields": {
        "relation_type": "string",
        "is_traversable": "boolean",
        "is_terminal": "boolean",
        "semantic_category": "string"
      }
    },
    "RelationPolicyRegistry": {
      "description": "Registry of access and traversal policies for relation types.",
      "fields": {
        "policies": "Map<string, RelationDefinition>"
      }
    },
    "EdgeEvidence": {
      "description": "Provenance and evidence supporting an edge.",
      "fields": {
        "source_id": "string",
        "extraction_method": "string",
        "confidence": "float"
      }
    },
    "DirectScoreComponents": {
      "description": "Explicit scoring components for an edge or path. No hidden LLM weights.",
      "fields": {
        "source_confidence": "float",
        "review_confidence": "float",
        "relation_specificity": "float",
        "context_fit": "float",
        "provenance_factor": "float",
        "path_specificity": "float"
      }
    },
    "PathCandidate": {
      "description": "A potential traversal path evaluated for scoring.",
      "fields": {
        "nodes": "List<string>",
        "edges": "List<string>"
      }
    },
    "PathDecision": {
      "description": "The final decision on whether a PathCandidate is accepted or rejected.",
      "fields": {
        "status": "enum { ACCEPTED, REJECTED }",
        "final_score": "float",
        "explanation": "ExplanationPayload"
      }
    },
    "BlockingReason": {
      "description": "Reason why a path or edge was blocked during traversal.",
      "fields": {
        "code": "string",
        "description": "string"
      }
    },
    "ExplanationPayload": {
      "description": "Detailed explanation for accepted or rejected paths.",
      "fields": {
        "accepted_path": "object",
        "rejected_path": "object"
      }
    }
  },
  "behaviors": {
    "missing_value": "fail-closed",
    "review_status": {
      "APPROVED": "eligible",
      "PENDING": "excluded by default",
      "REJECTED": "always blocked",
      "UNKNOWN": "blocked"
    }
  }
}"""

f2 = """{
  "ExplanationPayload": {
    "accepted_path": {
      "description": "Explanation for a path that successfully passed all gates and scoring.",
      "type": "object",
      "properties": {
        "path_id": { "type": "string" },
        "nodes": { "type": "array", "items": { "type": "string" } },
        "edges": { "type": "array", "items": { "type": "string" } },
        "score_components": { "$ref": "#/entities/DirectScoreComponents" },
        "hub_penalty_applied": { "type": "number", "description": "The penalty factor applied based on effective degree" },
        "final_score": { "type": "number" },
        "decision_rationale": { "type": "string" }
      }
    },
    "rejected_path": {
      "description": "Explanation for a path that was rejected due to policies or scores.",
      "type": "object",
      "properties": {
        "path_id": { "type": "string" },
        "candidate_nodes": { "type": "array", "items": { "type": "string" } },
        "candidate_edges": { "type": "array", "items": { "type": "string" } },
        "blocking_reasons": {
          "type": "array",
          "items": { "$ref": "#/entities/BlockingReason" }
        },
        "rejection_point_node_or_edge_id": { "type": "string" }
      }
    }
  }
}"""

f3 = """# Gate B Scoring Contract

## 1. Direct Score Components
The direct score must expose the following components explicitly. No components may be hidden inside an LLM call. The `context_fit` component MUST be deterministic.
- `source_confidence`
- `review_confidence`
- `relation_specificity`
- `context_fit`
- `provenance_factor`
- `path_specificity`

## 2. Effective Degree Definition
For the purposes of applying hub penalties, the effective degree of a node counts **only**:
- Approved edges
- Inferential edges
- Traversable edges
- In-scope edges
- Non-terminal edges

The following are explicitly **excluded** from the effective degree calculation:
- Aliases
- Candidate links
- Source links
- Navigation-only relations
- Rejected relations
- Pending relations
- Shadow data outside active pilot
- Exercise terminal edges

## 3. Hub Penalty Contract
The hub penalty mechanism must be configurable via the following parameters:
- `free_degree`: The number of connections a node may have before any penalty is applied.
- `alpha`: The scaling factor determining the rate of penalty application.
- `minimum_factor`: The floor value for the penalty (must not drop below this value).

**Requirements**:
1. **Monotonicity**: The penalty must monotonically increase (i.e., the multiplier factor must monotonically decrease) as the effective degree increases beyond `free_degree`.
2. **Floor**: The penalty multiplier must have a strict floor defined by `minimum_factor`.
3. **No Silently Invented Weights**: No clinically meaningful numeric weights may be silently invented. All weights must be explicitly defined in configuration, or default to a missing/fail-closed behavior.
"""

with open('docs/gate_b_discovery/GATE_B_INTERFACE_CONTRACT.json', 'w') as f: f.write(f1)
with open('docs/gate_b_discovery/GATE_B_EXPLAINABILITY_CONTRACT.json', 'w') as f: f.write(f2)
with open('docs/gate_b_discovery/GATE_B_SCORING_CONTRACT.md', 'w') as f: f.write(f3)

hasher = hashlib.sha256()
hasher.update(f1.encode('utf-8'))
hasher.update(f2.encode('utf-8'))
hasher.update(f3.encode('utf-8'))
digest = hasher.hexdigest()

f4 = f"""# Gate B Acceptance Contract

## Acceptance Requirements

### Behaviors
- **Missing-value behavior**: Default is fail-closed.
- **Required review behavior**:
  - `APPROVED`: eligible
  - `PENDING`: excluded by default
  - `REJECTED`: always blocked
  - `UNKNOWN`: blocked

### Entities Defined
The following entities are explicitly defined across the Interface and Explainability contracts:
- `RelationDefinition`
- `RelationPolicyRegistry`
- `EdgeEvidence`
- `DirectScoreComponents`
- `PathCandidate`
- `PathDecision`
- `BlockingReason`
- `ExplanationPayload`

## Contract State
contract_version: 1.0.0
contract_sha256: {digest}
status: FROZEN_FOR_GATE_B_IMPLEMENTATION
"""

with open('docs/gate_b_discovery/GATE_B_ACCEPTANCE_CONTRACT.md', 'w') as f: f.write(f4)
