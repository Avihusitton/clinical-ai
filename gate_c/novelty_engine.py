from typing import List, Protocol
from .models import NoveltyCandidate, NoveltyType, NoveltyDecision, ContradictionRecord
from .known_knowledge import KnownKnowledgeProvider
from .explainability import ExplainabilityEngine
from .exceptions import UnknownThresholdError

class DuplicateDetector(Protocol):
    def is_duplicate(self, candidate: NoveltyCandidate) -> bool:
        ...

class ContradictionDetector(Protocol):
    def check_contradictions(self, candidate: NoveltyCandidate) -> List[ContradictionRecord]:
        ...

class ScopeValidator(Protocol):
    def is_in_scope(self, candidate: NoveltyCandidate) -> bool:
        ...

class NoveltyEngine:
    def __init__(
        self,
        knowledge_provider: KnownKnowledgeProvider,
        duplicate_detector: DuplicateDetector,
        contradiction_detector: ContradictionDetector,
        scope_validator: ScopeValidator,
        threshold: float
    ):
        """
        Initializes the NoveltyEngine with injected dependencies.
        No direct Neo4j dependency, no LLM calls.
        """
        self.knowledge_provider = knowledge_provider
        self.duplicate_detector = duplicate_detector
        self.contradiction_detector = contradiction_detector
        self.scope_validator = scope_validator
        
        # UNKNOWN thresholds fail closed.
        if threshold is None or threshold < 0:
            raise UnknownThresholdError("Threshold is missing or invalid. Failing closed.")
            
        self.threshold = threshold
        self.explainability = ExplainabilityEngine()

    def process_candidate(self, candidate: NoveltyCandidate) -> NoveltyDecision:
        reasons = []
        
        # 1. PHI Check
        if candidate.evidence_bundle.contains_phi:
            reasons.append("Identifiable patient information detected. Rejected.")
            return self.explainability.explain(candidate, NoveltyType.OUT_OF_SCOPE, reasons)
            
        # 2. Provenance Check
        if not candidate.evidence_bundle.has_provenance:
            reasons.append("Missing provenance in evidence bundle. Failing closed.")
            return self.explainability.explain(candidate, NoveltyType.INSUFFICIENT_EVIDENCE, reasons)

        # 3. Scope Validation (e.g. rejects autonomous clinical requests)
        if not self.scope_validator.is_in_scope(candidate):
            reasons.append("Candidate is out of scope (e.g. autonomous clinical request).")
            return self.explainability.explain(candidate, NoveltyType.OUT_OF_SCOPE, reasons)
            
        # 4. Known Knowledge Comparison
        kk_check = self.knowledge_provider.check_candidate(candidate)
        if kk_check.is_known:
            reasons.append(f"Candidate matches known knowledge. Reference: {kk_check.existing_reference}")
            return self.explainability.explain(candidate, NoveltyType.KNOWN_KNOWLEDGE, reasons)

        # 5. Duplicate Detection
        if self.duplicate_detector.is_duplicate(candidate):
            reasons.append("Candidate is a possible duplicate.")
            return self.explainability.explain(candidate, NoveltyType.POSSIBLE_DUPLICATE, reasons)

        # 6. Contradiction Detection
        contradictions = self.contradiction_detector.check_contradictions(candidate)
        if contradictions:
            # Contradictory evidence remains visible
            reasons.append(f"Contradictory evidence found: {len(contradictions)} records.")
            for c in contradictions:
                reasons.append(f"Contradiction: {c.reasoning}")
            return self.explainability.explain(candidate, NoveltyType.POSSIBLE_CONTRADICTION, reasons)

        # 7. Evidence Validation (Threshold Check)
        max_conf = max((item.confidence for item in candidate.evidence_bundle.items), default=0.0)
        if max_conf < self.threshold:
            reasons.append(f"Max confidence {max_conf} below required threshold {self.threshold}.")
            return self.explainability.explain(candidate, NoveltyType.INSUFFICIENT_EVIDENCE, reasons)
            
        # All checks passed, classify as NEW_RELATION_CANDIDATE
        reasons.append("Candidate passed all deterministic checks.")
        
        # Status remains DISCOVERY_ONLY and requires PENDING_HUMAN_REVIEW
        return self.explainability.explain(candidate, NoveltyType.NEW_RELATION_CANDIDATE, reasons)
