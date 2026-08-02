# Gate C Data Flow (Novelty Decision Flow)

The discovery pipeline follows an 8-step unidirectional data flow to ensure safety and rigor.

## Step 1: Candidate Generation
Unstructured texts are mined to form initial hypotheses. Emits `NoveltyCandidate`.

## Step 2: Known-Knowledge Comparison
The candidate is run against the verified knowledge graph. `KnownKnowledgeCheck` evaluates semantic distance.

## Step 3: Duplicate Detection
Candidate is checked for aliases. If it is merely a new name for an existing entity, it flags as `POSSIBLE_DUPLICATE` or `MISSING_ALIAS`.

## Step 4: Evidence Validation
`EvidenceBundle` is scored for `source_confidence`, `provenance_quality`, and `evidence_consistency`. Low scores may result in `INSUFFICIENT_EVIDENCE`.

## Step 5: Contradiction Detection
Candidate claims are inverted and searched against established truth. If matches occur, `ContradictionRecord` is created. Category may shift to `POSSIBLE_CONTRADICTION`.

## Step 6: Scope Validation
Candidate is evaluated against system boundaries (`scope_fit`). Out of domain findings are marked `OUT_OF_SCOPE`.

## Step 7: Novelty Classification
A final `NoveltyType` is assigned based on the aggregation of checks and `NoveltyScoreComponents`. Fallbacks for unknown thresholds default to safe, closed classifications.

## Step 8: Human-Review Routing
`NoveltyDecision` is attached, explicitly forcing `safety_mode: DISCOVERY_ONLY` and status to `PENDING_HUMAN_REVIEW`. The candidate is pushed to the reviewer queue.
