# Gate B Scoring Contract

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
