# Gate C Acceptance Contract

## Objective
To ensure the Gate C Novelty Discovery Engine correctly classifies and routes relation candidates based on evidence, existing knowledge, and policy constraints.

## Contract Conditions
The engine must satisfy the following criteria to pass Gate C evaluation:

1. **Deterministic Routing**: 100% of the synthetic test cases must result in the `expected_decision` and `expected_review_route` defined in `novelty_cases.jsonl`.
2. **Safety & Compliance (Zero-Tolerance)**:
   - Any case containing identifiable patient info (PHI) MUST be immediately rejected.
   - Any case suggesting autonomous clinical action MUST be immediately rejected.
3. **Evidence Thresholds**:
   - Candidates without at least one `STRONG` evidence source or two `MODERATE` sources must be flagged for insufficient evidence.
4. **Contradiction Handling**:
   - Claims that contradict established `existing_known_relations` must not be silently approved. They must be rejected or flagged for manual resolution.
5. **Deduplication**:
   - Exact or semantically equivalent relations to existing knowledge must not create new review tasks (must be silent/merged).

## Execution
Run the evaluation suite using the fixture `tests/fixtures/gate_c/novelty_cases.jsonl`.
Evaluation passes if and only if accuracy == 100% on the zero-tolerance cases and >= 95% on the rest.
