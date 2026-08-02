from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class NoveltyType(str, Enum):
    NEW_RELATION_CANDIDATE = "NEW_RELATION_CANDIDATE"
    MISSING_OFFICIAL_ENTRY = "MISSING_OFFICIAL_ENTRY"
    MISSING_ALIAS = "MISSING_ALIAS"
    POSSIBLE_CONTRADICTION = "POSSIBLE_CONTRADICTION"
    POSSIBLE_DUPLICATE = "POSSIBLE_DUPLICATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    KNOWN_KNOWLEDGE = "KNOWN_KNOWLEDGE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"

class EvidenceItem(BaseModel):
    source_id: str
    content: str
    provenance: str
    confidence: float

class EvidenceBundle(BaseModel):
    items: List[EvidenceItem]
    contains_phi: bool = False
    
    @property
    def has_provenance(self) -> bool:
        """Fails closed if any evidence item lacks provenance."""
        if not self.items:
            return False
        return all(bool(item.provenance) for item in self.items)

class NoveltyScoreComponents(BaseModel):
    evidence_score: float
    uniqueness_score: float
    confidence_score: float

class NoveltyCandidate(BaseModel):
    candidate_id: str
    source_entity: str
    target_entity: str
    relation_type: str
    evidence_bundle: EvidenceBundle
    status: str = Field(default="DISCOVERY_ONLY", frozen=True)
    review_status: str = Field(default="PENDING_HUMAN_REVIEW")
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KnownKnowledgeCheck(BaseModel):
    is_known: bool
    existing_reference: Optional[str] = None
    similarity_score: float

class ContradictionRecord(BaseModel):
    candidate_id: str
    contradictory_evidence: str
    reasoning: str

class ReviewDecision(BaseModel):
    candidate_id: str
    decision: str
    reviewer: str
    comments: str

class NoveltyExplanation(BaseModel):
    candidate_id: str
    decision: str
    reasoning: List[str]

class NoveltyDecision(BaseModel):
    candidate: NoveltyCandidate
    novelty_type: NoveltyType
    explanation: NoveltyExplanation
