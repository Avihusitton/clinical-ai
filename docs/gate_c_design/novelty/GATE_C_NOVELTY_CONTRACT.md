# Gate C Novelty Contract Design

## 1. Overview
Gate C defines the design boundaries and requirements for discovering potentially new knowledge without treating it as approved knowledge. It acts as a safety gate for new findings (NoveltyCandidates) ensuring they are flagged for human review and never automatically promoted.

## 2. Safety Behavior (Strict Requirements)
- **Status Restrictions**: Every candidate MUST be classified as `DISCOVERY_ONLY` and `PENDING_HUMAN_REVIEW`.
- **Absolute Prohibitions**:
  - NEVER mark a discovery as clinical truth.
  - NEVER promote a discovery automatically.
  - NEVER overwrite official glossaries or established relations.
  - NEVER write inferred edges permanently to the Neo4j knowledge graph.
  - NEVER hide contradictions from reviewers.
  - NEVER produce autonomous treatment conclusions.

## 3. Entities
- **NoveltyCandidate**: The core entity representing a newly discovered potential relationship or fact.
- **NoveltyType**: Classification of the novelty candidate.
- **KnownKnowledgeCheck**: Assessment against existing verified knowledge to ensure the candidate is truly novel.
- **EvidenceBundle**: A collection of evidence supporting the novelty candidate.
- **EvidenceItem**: A single piece of evidence (e.g., paper, excerpt, database record).
- **ContradictionRecord**: Detailed recording of any contradictions found between the candidate and existing knowledge or within the evidence itself.
- **NoveltyScoreComponents**: Granular scoring of the candidate across multiple dimensions.
- **NoveltyDecision**: The final algorithmic decision routing the candidate.
- **ReviewDecision**: The decision made by a human reviewer.
- **NoveltyExplanation**: Transparent, human-readable justification for the generated novelty candidate.

## 4. Novelty Categories
Must be one of the following:
- `NEW_RELATION_CANDIDATE`
- `MISSING_OFFICIAL_ENTRY`
- `MISSING_ALIAS`
- `POSSIBLE_CONTRADICTION`
- `POSSIBLE_DUPLICATE`
- `INSUFFICIENT_EVIDENCE`
- `KNOWN_KNOWLEDGE`
- `OUT_OF_SCOPE`

## 5. Novelty Score Components
All score components must have explicit/provisional thresholds or fallback to `UNKNOWN` (which fails closed, triggering human review).
- `source_confidence`: Confidence in the origin of the information.
- `evidence_consistency`: Degree to which multiple evidence items agree.
- `provenance_quality`: Traceability and reliability of the evidence chain.
- `semantic_distance_from_known_knowledge`: How conceptually far the finding is from existing entries.
- `duplicate_risk`: Probability that this is a known fact disguised by aliases.
- `contradiction_risk`: Probability that this finding contradicts established truth.
- `scope_fit`: Alignment with the clinical boundaries of the system.
