# Gate C Review Workflow

## 1. Introduction
The novelty review workflow enforces strict safety constraints to prevent unverified machine-generated hypotheses from entering the clinical truth base.

## 2. Review States
- **DISCOVERY_ONLY**: The candidate is held in an isolated discovery state.
- **PENDING_HUMAN_REVIEW**: The candidate is enqueued for review.
- **REVIEW_APPROVED**: Only achieved via explicit human action.
- **REVIEW_REJECTED**: Discarded or archived as an anti-pattern/negative sample.
- **NEEDS_MORE_EVIDENCE**: Pushed back to the discovery engine to gather more literature.

## 3. Human Review Process
1. **Intake**: Reviewer selects a `NoveltyCandidate` in `PENDING_HUMAN_REVIEW`.
2. **Explainability Audit**: Reviewer reads the `NoveltyExplanation` and checks the `NoveltyScoreComponents`. Any `UNKNOWN` score demands deep scrutiny.
3. **Evidence Validation**: Reviewer inspects the `EvidenceBundle` to confirm origin reliability.
4. **Contradiction Check**: If `ContradictionRecord` exists, the reviewer MUST NOT hide it and must determine if the novelty overrides existing knowledge or is an error.
5. **Decision Execution**: Reviewer submits a `ReviewDecision` (Approved, Rejected, Needs Evidence).

## 4. Safety Guardrails During Review
- Automated promotion is physically blocked at the API level for NoveltyCandidates.
- Inferred edges are NEVER written permanently to Neo4j until the `REVIEW_APPROVED` state is achieved by a human.
- Clinical truth/glossary remains read-only during the entire discovery phase.
