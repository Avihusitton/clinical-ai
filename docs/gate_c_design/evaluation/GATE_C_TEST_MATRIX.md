# Gate C Test Matrix: Novelty Discovery Engine

## Overview
This matrix defines the synthetic test coverage for the Gate C Novelty Discovery engine. The tests are designed to evaluate the engine's ability to classify input statements into novelty categories and route them appropriately without executing actual database updates.

## Fixture Groups
1. **Known-Knowledge Cases (10 cases)**
   - Covers: Exact known relations, semantically equivalent known relations.
   - Expected Decision: `APPROVE_SILENT` or `DROP_DUPLICATE` (No review required).

2. **Valid Novelty-Candidate Cases (10 cases)**
   - Covers: New relation candidates, missing aliases, missing official entries.
   - Expected Decision: `ROUTE_TO_REVIEW`.
   - Expected Route: Domain-specific review (e.g., `MEDICAL_REVIEW`).

3. **Duplicate or Near-Duplicate Cases (10 cases)**
   - Covers: Duplicate wordings, overlapping claims with existing knowledge.
   - Expected Decision: `MERGE` or `REJECT`.

4. **Insufficient-Evidence Cases (10 cases)**
   - Covers: Unsupported claims, single weak sources, candidates lacking provenance.
   - Expected Decision: `REJECT`.
   - Blocking Reasons: `INSUFFICIENT_EVIDENCE`, `LACKS_PROVENANCE`, `CONFLICTING_SOURCES`.

5. **Contradiction Cases (10 cases)**
   - Covers: Contradictions with approved knowledge, conflicting sources within the input.
   - Expected Decision: `REJECT` or `ROUTE_TO_RESOLUTION`.
   - Blocking Reasons: `CONTRADICTS_KNOWN_KNOWLEDGE`.

6. **Out-of-Scope Cases (10 cases)**
   - Covers: Relations outside approved registry, identifiable patient info, autonomous clinical action requests.
   - Expected Decision: `REJECT`.
   - Blocking Reasons: `PHI_DETECTED`, `AUTONOMOUS_ACTION_NOT_PERMITTED`, `OUTSIDE_REGISTRY`.

## Required Behavior Coverage Mapping
- [x] exact known relation -> Group 1
- [x] semantically equivalent known relation -> Group 1
- [x] new relation candidate -> Group 2
- [x] missing alias -> Group 2
- [x] missing official entry -> Group 2
- [x] unsupported claim -> Group 4
- [x] single weak source -> Group 4
- [x] conflicting sources -> Group 4
- [x] duplicate wording -> Group 3
- [x] contradiction with approved knowledge -> Group 5
- [x] relation outside approved registry -> Group 6
- [x] candidate involving Exercise bridge -> Group 2 / Group 6
- [x] candidate lacking provenance -> Group 4
- [x] candidate containing identifiable patient info -> Group 6
- [x] candidate requesting autonomous clinical action -> Group 6
