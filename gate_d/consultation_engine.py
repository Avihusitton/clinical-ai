from datetime import datetime
from typing import List

from .models import (
    ConsultationRequest, ConsultationResponse, ClinicalPossibility,
    AlternativeInterpretation, UncertaintyStatement, TherapistDecision,
    TherapistFeedback
)
from .safety_policy import SafetyPolicy
from .language_policy import LanguagePolicy
from .evidence_filter import EvidenceFilter
from .audit_trail import AuditTrail
from .exceptions import GateDException

class ConsultationEngine:
    def __init__(self):
        self.safety_policy = SafetyPolicy()
        self.language_policy = LanguagePolicy()
        self.evidence_filter = EvidenceFilter()
        self.audit_trail = AuditTrail()

    def process_request(self, request: ConsultationRequest) -> ConsultationResponse:
        self.audit_trail.log_event(
            event_type="CONSULTATION_REQUEST_RECEIVED",
            therapist_id=request.context.therapist_id,
            request_id=request.request_id,
            details={"query_intent": request.question.intent}
        )

        try:
            # Enforce Safety Boundaries (No PII, No forbidden actions)
            boundaries = self.safety_policy.apply_safety_boundaries(request)

            # Filter Evidence
            valid_evidence = self.evidence_filter.filter_evidence(request.provided_evidence)
            
            official_entries = [e for e in valid_evidence if e.source_type == "Official Guideline"]
            retrieved_entries = [e for e in valid_evidence if e.source_type != "Official Guideline"]

            # Generate deterministic Clinical Possibilities
            raw_possibilities = []
            if request.question.intent == "explore_coping_strategies":
                raw_possibilities.append("The client is struggling with emotional regulation.")
                
            # Enforce Language Policy & Evidence constraints
            self.evidence_filter.ensure_supported_claims(raw_possibilities, valid_evidence)
            
            clinical_possibilities = []
            for p in raw_possibilities:
                safe_text = self.language_policy.review_clinical_possibility(p)
                clinical_possibilities.append(
                    ClinicalPossibility(
                        description=safe_text,
                        supporting_evidence_ids=[e.source_id for e in valid_evidence]
                    )
                )

            # Generate Uncertainties and Alternative Interpretations
            uncertainties = [
                UncertaintyStatement(
                    topic="Client's full history",
                    reason="Not all historical context is provided in this anonymous consultation."
                )
            ]
            
            alternatives = []
            if request.question.intent == "explore_coping_strategies":
                alternatives.append(
                    AlternativeInterpretation(
                        description=self.language_policy.enforce_possibility_language("The issue is environmental stress rather than internal regulation."),
                        reason="Lack of data on current life stressors."
                    )
                )

            audit_metadata = {
                "processed_at": datetime.utcnow().isoformat(),
                "evidence_count": len(valid_evidence),
                "engine_version": "1.0.0-deterministic"
            }

            response = ConsultationResponse(
                request_summary=f"Consultation regarding: {request.question.query_text[:50]}...",
                relevant_official_entries=official_entries,
                retrieved_evidence=retrieved_entries,
                possible_interpretations=clinical_possibilities,
                alternative_interpretations=alternatives,
                uncertainties=uncertainties,
                missing_information=["Specific environmental triggers", "Recent life changes"],
                safety_boundaries=boundaries,
                optional_reflection_questions=["How does the client describe their physical sensations during distress?"],
                optional_reviewed_exercises=[{"name": "Grounding Exercise 5-4-3-2-1", "description": "A sensory grounding technique."}],
                therapist_decision_required=True, # Therapist retains full decision authority
                audit_metadata=audit_metadata
            )

            self.audit_trail.log_event(
                event_type="CONSULTATION_RESPONSE_GENERATED",
                therapist_id=request.context.therapist_id,
                request_id=request.request_id,
                details=audit_metadata
            )

            return response

        except GateDException as e:
            self.audit_trail.log_event(
                event_type="CONSULTATION_REJECTED",
                therapist_id=request.context.therapist_id,
                request_id=request.request_id,
                details={"error_type": type(e).__name__, "error_message": str(e)}
            )
            raise

    def process_therapist_decision(self, decision: TherapistDecision):
        self.audit_trail.log_event(
            event_type="THERAPIST_DECISION_RECORDED",
            therapist_id="UNKNOWN", # In practice, this would come from the session context or request context
            request_id=decision.request_id,
            details={
                "decision_id": decision.decision_id,
                "accepted_count": len(decision.accepted_interpretations),
                "rejected_count": len(decision.rejected_interpretations),
                "has_modifications": len(decision.modifications) > 0
            }
        )

    def process_therapist_feedback(self, feedback: TherapistFeedback):
        self.audit_trail.log_event(
            event_type="THERAPIST_FEEDBACK_RECORDED",
            therapist_id="UNKNOWN", 
            request_id="UNKNOWN",
            details={
                "feedback_id": feedback.feedback_id,
                "rating": feedback.usefulness_rating
            }
        )
