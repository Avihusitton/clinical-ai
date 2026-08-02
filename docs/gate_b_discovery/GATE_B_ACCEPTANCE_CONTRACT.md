# Gate B Acceptance Contract

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
contract_sha256: 4afa12f02fa95763305e8d19beb40666e6922a2c934e20e147983cd91c116fce
status: FROZEN_FOR_GATE_B_IMPLEMENTATION
