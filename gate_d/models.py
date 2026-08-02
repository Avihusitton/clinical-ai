from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime

@dataclass(frozen=True)
class ConsultationContext:
    session_id: str
    therapist_id: str
    anonymized_client_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class ConsultationQuestion:
    question_id: str
    query_text: str
    intent: str

@dataclass(frozen=True)
class EvidenceReference:
    source_id: str
    source_type: str
    content_summary: str
    is_reviewed: bool = False

@dataclass(frozen=True)
class ConsultationRequest:
    request_id: str
    context: ConsultationContext
    question: ConsultationQuestion
    provided_evidence: List['EvidenceReference'] = field(default_factory=list)

@dataclass(frozen=True)
class ClinicalPossibility:
    description: str
    supporting_evidence_ids: List[str]

@dataclass(frozen=True)
class UncertaintyStatement:
    topic: str
    reason: str
    
@dataclass(frozen=True)
class AlternativeInterpretation:
    description: str
    reason: str

@dataclass(frozen=True)
class SafetyBoundary:
    boundary_type: str
    description: str
    enforced: bool = True

@dataclass(frozen=True)
class ConsultationResponse:
    request_summary: str
    relevant_official_entries: List[EvidenceReference]
    retrieved_evidence: List[EvidenceReference]
    possible_interpretations: List[ClinicalPossibility]
    alternative_interpretations: List[AlternativeInterpretation]
    uncertainties: List[UncertaintyStatement]
    missing_information: List[str]
    safety_boundaries: List[SafetyBoundary]
    optional_reflection_questions: List[str]
    optional_reviewed_exercises: List[Dict[str, str]]
    therapist_decision_required: bool
    audit_metadata: Dict[str, Any]

@dataclass(frozen=True)
class TherapistDecision:
    decision_id: str
    request_id: str
    accepted_interpretations: List[str]
    rejected_interpretations: List[str]
    modifications: Dict[str, str]
    timestamp: datetime = field(default_factory=datetime.utcnow)

@dataclass(frozen=True)
class TherapistFeedback:
    feedback_id: str
    decision_id: str
    comments: str
    usefulness_rating: int

@dataclass(frozen=True)
class ConsultationAuditEvent:
    event_id: str
    event_type: str
    request_id: Optional[str]
    therapist_id: str
    details: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.utcnow)
