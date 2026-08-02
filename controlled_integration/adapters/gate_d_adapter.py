"""
controlled_integration/adapters/gate_d_adapter.py
--------------------------------------------------
Adapter wrapping Gate D consultation engine (gate_d/models.py, gate_d/consultation_engine.py).
Consumes screened ConsultationInputBundle to produce ConsultationOutputBundle.
"""

from typing import Dict, Any, List, Optional
from gate_d.models import (
    ConsultationRequest, ConsultationContext, ConsultationQuestion,
    EvidenceReference, ConsultationResponse
)
from gate_d.consultation_engine import ConsultationEngine
from ..models import ConsultationInputBundle, ConsultationOutputBundle, IntegrationRequest

class GateDAdapter:
    """
    Adapter bridging Gate D consultation engine.
    Requires input to be pre-screened by BoundaryAdapter.
    """
    def __init__(self, engine: Optional[ConsultationEngine] = None):
        self.engine = engine or ConsultationEngine()

    def process_consultation(
        self,
        request: IntegrationRequest,
        input_bundle: ConsultationInputBundle
    ) -> ConsultationOutputBundle:
        """
        Executes Gate D consultation generation using eligible screened evidence.
        """
        evidence_refs = [
            EvidenceReference(
                source_id=item["source_id"],
                source_type="Official Guideline",
                content_summary=item["content_summary"],
                is_reviewed=True
            )
            for item in input_bundle.eligible_official_evidence
        ]

        gate_d_req = ConsultationRequest(
            request_id=request.request_id,
            context=ConsultationContext(
                session_id=request.context.session_id,
                therapist_id=request.context.user_id,
                anonymized_client_id="ANON_CLIENT_001"
            ),
            question=ConsultationQuestion(
                question_id=f"q_{request.request_id[:8]}",
                query_text=request.query_text,
                intent="explore_coping_strategies"
            ),
            provided_evidence=evidence_refs
        )

        resp: ConsultationResponse = self.engine.process_request(gate_d_req)

        interpretations = [
            {"description": p.description, "supporting_evidence_ids": p.supporting_evidence_ids}
            for p in resp.possible_interpretations
        ]
        alternatives = [
            {"description": a.description, "reason": a.reason}
            for a in resp.alternative_interpretations
        ]
        uncertainties = [
            {"topic": u.topic, "reason": u.reason}
            for u in resp.uncertainties
        ]
        boundaries = [
            {"boundary_type": sb.boundary_type, "description": sb.description, "enforced": sb.enforced}
            for sb in resp.safety_boundaries
        ]

        return ConsultationOutputBundle(
            request_summary=resp.request_summary,
            official_entries=[{"source_id": e.source_id, "summary": e.content_summary} for e in resp.relevant_official_entries],
            interpretations=interpretations,
            alternatives=alternatives,
            uncertainties=uncertainties,
            safety_boundaries=boundaries,
            therapist_decision_required=resp.therapist_decision_required
        )
